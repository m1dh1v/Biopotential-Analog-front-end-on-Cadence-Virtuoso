"""Run a Spectre netlist on the EDA server (ssh alias eda-uni) and fetch PSF-ASCII results."""
import os, subprocess, shutil, glob

HERE = os.path.dirname(os.path.abspath(__file__))
REMOTE = "Desktop/cmos65/sim/afe"


def run(name, text, quiet=False):
    loc = os.path.join(HERE, "net", name + ".scs")
    with open(loc, "w", newline="\n") as f:
        f.write(text + "\n")
    subprocess.run(["scp", "-O", "-q", "net/%s.scs" % name, "eda-uni:%s/" % REMOTE], check=True, cwd=HERE)
    out = subprocess.run(["ssh", "eda-uni", "rm -rf ~/%s/%s.raw; ~/%s/runsp.sh %s.scs %s.raw" % (REMOTE, name, REMOTE, name, name)],
                         capture_output=True, text=True).stdout
    if not quiet:
        print(out.strip())
    rd = os.path.join(HERE, "raw", name)
    shutil.rmtree(rd, ignore_errors=True)
    os.makedirs(rd)
    subprocess.run(["scp", "-O", "-q", "eda-uni:%s/%s.raw/*" % (REMOTE, name), "raw/%s/" % name], check=False, cwd=HERE)
    subprocess.run(["scp", "-O", "-q", "eda-uni:%s/%s.raw.log" % (REMOTE, name), "raw/%s/spectre.log" % name], check=False, cwd=HERE)
    if "completes with 0 errors" not in out:
        raise RuntimeError("spectre failed for %s:\n%s" % (name, out))
    return rd
