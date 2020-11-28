import sys
import os
from cytomine.models import Job
from subprocess import call
from biaflows import CLASS_OBJSEG
from biaflows.helpers import BiaflowsJob, prepare_data, upload_data, upload_metrics

def parseCPparam(bj, pipeline, tmpdir):
    """
    """
    sp = bj.software.parameters
    cpparams = {}
    for param in sp:
        cpparams[param['humanName']] = param['name']

    mod_pipeline = os.path.join(tmpdir,os.path.basename(pipeline))
    rhdl = open(pipeline)
    whdl = open(mod_pipeline,"w")
    for line in rhdl:
        ar = line.split(":")
        if ar[0].strip() in cpparams.keys():
            line = ar[0] + ":" + str(getattr(bj.parameters,cpparams[ar[0].strip()]))+"\n"
        whdl.write(line)

    return mod_pipeline


def main(argv):
    base_path = "{}".format(os.getenv("HOME")) # Mandatory for Singularity
    problem_cls = CLASS_OBJSEG

    with BiaflowsJob.from_cli(argv) as bj:
        bj.job.update(status=Job.RUNNING, progress=0, statusComment="Initialisation...")
        # 1. Prepare data for workflow
        in_imgs, gt_imgs, in_path, gt_path, out_path, tmp_path = prepare_data(problem_cls, bj, is_2d=True, **bj.flags)

        plugindir = "/app/plugins"
        pipeline = "/app/CP_detect_nuclei.cppipe"
        file_list = os.path.join(tmp_path,"file_list.txt")
        fh = open(file_list,"w")
        for image in in_imgs:
            fh.write(image.filepath+"\n")
        fh.close()

        # 2. Run CellProfiler pipeline
        bj.job.update(progress=25, statusComment="Launching workflow...")
        mod_pipeline = parseCPparam(bj, pipeline, tmp_path)
        
        shArgs = [
            "python", "/app/CellProfiler/CellProfiler.py", "-c", "-r", "-b", "--do-not-fetch", "-p", mod_pipeline,
            "-i", in_path, "-o", out_path, "-t", tmp_path, "--plugins-directory", plugindir, "--file-list", file_list
        ]
        return_code = call(" ".join(shArgs), shell=True, cwd="/app/CellProfiler")

        if return_code != 0:
            err_desc = "Failed to execute the CellProfiler pipeline (return code: {})".format(return_code)
            bj.job.update(progress=50, statusComment=err_desc)
            raise ValueError(err_desc)

        # 3. Upload data to BIAFLOWS
        upload_data(problem_cls, bj, in_imgs, out_path, **bj.flags, monitor_params={
            "start": 60, "end": 90, "period": 0.1,
            "prefix": "Extracting and uploading polygons from masks"})
        
        # 4. Compute and upload metrics
        bj.job.update(progress=90, statusComment="Computing and uploading metrics...")
        upload_metrics(problem_cls, bj, in_imgs, gt_path, out_path, tmp_path, **bj.flags)

        # 5. Pipeline finished
        bj.job.update(progress=100, status=Job.TERMINATED, status_comment="Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])
