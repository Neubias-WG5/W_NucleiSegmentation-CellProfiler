import sys
import os
import imageio
from cytomine import CytomineJob
from cytomine.models import *
from subprocess import run
from shapely.affinity import affine_transform
from annotation_exporter import mask_to_objects_2d

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
        working_path = os.path.join(base_path, "data", str(cj.job.id))
        indir = os.path.join(working_path, "in")
        makedirs(indir)
        outdir = os.path.join(working_path, "out")
        makedirs(outdir)
        tmpdir = os.path.join(working_path, "tmp")
        makedirs(tmpdir)
        plugindir = "/app/plugins"
        pipeline = "/app/CP_detect_nuclei.cppipe"
        file_list = os.path.join(tmpdir,"file_list.txt")

        cj.job.update(progress=1, statusComment="Downloading images (to {})...".format(indir))
        image_instances = ImageInstanceCollection().fetch_with_filter("project", cj.project.id)

        fh = open(file_list,"w")
        for image in image_instances:
            image.download(os.path.join(indir, "{id}.tif"))
            fh.write(os.path.join(indir,"{}.tif".format(image.id))+"\n")
        fh.close()

        mod_pipeline = parseCPparam(cj, pipeline, tmpdir)

        cj.job.update(progress=25, statusComment="Launching workflow...")

        # Create call to cellprofiler and execute
        shArgs = ["python"]
        shArgs.append("/CellProfiler/CellProfiler.py")
        shArgs.append("-c")
        shArgs.append("-r")
        shArgs.append("-b")
        shArgs.append("--do-not-fetch")
        shArgs.append("-p")
        shArgs.append(mod_pipeline)
        shArgs.append("-i")
        shArgs.append(indir)
        shArgs.append("-o")
        shArgs.append(outdir)
        shArgs.append("-t")
        shArgs.append(tmpdir)
        shArgs.append("--plugins-directory")
        shArgs.append(plugindir)
        shArgs.append("--file-list")
        shArgs.append(file_list)

        run(" ".join(shArgs), shell=True)
        cj.job.update(progress=75, status_comment="Extracting polygons...")
        
        annotations = AnnotationCollection()
        for image in cj.monitor(image_instances, start=75, end=95, period=0.1, prefix="Upload annotations"):
            resfn = str(image.id) + ".tif"
            respath = os.path.join(outdir, resfn)
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
        # TODO

        cj.job.update(progress=100, status=Job.TERMINATED, status_comment="Finished.")


if __name__ == "__main__":
    main()
