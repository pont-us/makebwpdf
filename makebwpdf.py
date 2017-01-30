#!/usr/bin/python3

import glob
import subprocess
import argparse

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--brightness", "-b",
                        type = str, nargs = 1,
                        default = "0")
    args = parser.parse_args()

    # good brightness: -0.35
    for filename in glob.glob("????.tiff"):
        outfile = filename[:-5] + "-bw.tiff" 
        subprocess.call(["econvert",
                        "-i", filename,
                        "--brightness", args.brightness[0],
                        "--colorspace", "bilevel",
                         "--output", outfile])
    subprocess.call("tiffcp -c g4 ????-bw.tiff all.tiff",
                    shell=True)
    subprocess.call(["tiff2pdf",
                    "-c", "g4",
                    "-x600", "-y600",
                    "-o", "all.pdf",
                     "all.tiff"])

if __name__ == "__main__":
    main()
