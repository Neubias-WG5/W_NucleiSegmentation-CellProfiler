import sys
import os
import imageio
import cv2
from cytomine import CytomineJob
from cytomine.models import *
from subprocess import run
from shapely.affinity import affine_transform
from annotation_exporter import mask_to_objects_2d
from neubiaswg5.metrics import computemetrics_batch

def makedirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

def parseCPparam(cj, pipeline, tmpdir):
    """
    """
    sp = cj.software.parameters
    cpparams = {}
    for param in sp:
        cpparams[param['humanName']] = param['name']

    mod_pipeline = os.path.join(tmpdir,os.path.basename(pipeline))
    rhdl = open(pipeline)
    whdl = open(mod_pipeline,"w")
    for line in rhdl:
        ar = line.split(":")
        if ar[0].strip() in cpparams.keys():
            line = ar[0] + ":" + str(getattr(cj.parameters,cpparams[ar[0].strip()]))+"\n"
        whdl.write(line)

    return mod_pipeline


def main():
    base_path = "{}".format(os.getenv("HOME")) # Mandatory for Singularity

    with CytomineJob.from_cli(sys.argv[1:]) as cj:
        cj.job.update(status=Job.RUNNING, progress=0, statusComment="Initialisation...")
        
        working_path = os.path.join(base_path, "data", str(cj.job.id))
        gt_suffix = "_lbl"
        in_path = os.path.join(working_path, "in")
        out_path = os.path.join(working_path, "out")
        tmp_path = os.path.join(working_path, "tmp")
        gt_path = os.path.join(working_path, "gt")
        plugindir = "/app/plugins"
        pipeline = "/app/CP_detect_nuclei.cppipe"
        file_list = os.path.join(tmp_path,"file_list.txt")
        if not os.path.exists(working_path):
            makedirs(in_path)
            makedirs(out_path)
            makedirs(tmp_path)
            makedirs(gt_path)

        cj.job.update(progress=1, statusComment="Downloading images (to {})...".format(in_path))
        image_instances = ImageInstanceCollection().fetch_with_filter("project", cj.parameters.cytomine_id_project)
        input_images = [i for i in image_instances if gt_suffix not in i.originalFilename]
        gt_images = [i for i in image_instances if gt_suffix in i.originalFilename]

        # Download images and write path to CP input file
        fh = open(file_list,"w")
        for image in input_images:
            image.download(os.path.join(in_path, "{id}.tif"))
            fh.write(os.path.join(in_path,"{}.tif".format(image.id))+"\n")
        fh.close()

        for gt_image in gt_images:
            related_name = gt_image.originalFilename.replace(gt_suffix, '')
            related_image = [i for i in input_images if related_name == i.originalFilename]
            if len(related_image) == 1:
                gt_image.download(os.path.join(gt_path, "{}.tif".format(related_image[0].id)))

        # Run CellProfiler pipeline
        cj.job.update(progress=25, statusComment="Launching workflow...")
        mod_pipeline = parseCPparam(cj, pipeline, tmp_path)
        
        # Create call to cellprofiler and execute
        shArgs = [
            "python", "/CellProfiler/CellProfiler.py", "-c", "-r", "-b", "--do-not-fetch", "-p", mod_pipeline,
            "-i", in_path, "-o", out_path, "-t", tmp_path, "--plugins-directory", plugindir, "--file-list", file_list
        ]
        run(" ".join(shArgs), shell=True)
        cj.job.update(progress=75, status_comment="Extracting polygons...")
        
        annotations = AnnotationCollection()
        for image in cj.monitor(image_instances, start=75, end=95, period=0.1, prefix="Upload annotations"):
            resfn = str(image.id) + ".tif"
            respath = os.path.join(out_path, resfn)
            if os.path.isfile(respath):
                img = imageio.imread(respath)
                slices = mask_to_objects_2d(img)

                for obj_slice in slices:
                    annotations.append(Annotation(
                        location=affine_transform(obj_slice.polygon, [1, 0, 0, -1, 0, image.height]).wkt,
                        id_image=image.id, id_project=cj.parameters.cytomine_id_project,
                        property=[{"key": "index", "value": str(obj_slice.label)}]
                    ))

                    if len(annotations) % 100 == 0:
                        annotations.save()
                        annotations = AnnotationCollection()
            else:
                print("No output file at '{}' for image with id:{}.".format(respath, image.id), file=sys.stderr)
        
        # Save last annotations
        annotations.save()

        # Launch the metrics computation here
        cj.job.update(progress=90, statusComment="Computing and uploading metrics...")
        
        outfiles, reffiles = zip(*[
            (os.path.join(out_path, "{}.tif".format(image.id)),
             os.path.join(gt_path, "{}.tif".format(image.id)))
            for image in input_images
        ])

        results = computemetrics_batch(outfiles, reffiles, "ObjSeg", tmp_path)

        for key, value in results.items():
            Property(cj.job, key=key, value=str(value)).save()
        Property(cj.job, key="IMAGE_INSTANCES", value=str([im.id for im in input_images])).save()

        cj.job.update(progress=100, status=Job.TERMINATED, status_comment="Finished.")


if __name__ == "__main__":
    main()
