#!/usr/bin/python3

"""
Convert a series of image files to a multi-page bilevel (i.e. black and
white) PDF.

Requires: econvert (from https://exactcode.com/opensource/exactimage/ ),
tiffcp, and tiff2pdf.

By Pontus Lurcock, 2017 (pont -at- talvi.net).
Released into the public domain.
"""

import subprocess
import argparse
import os
import os.path
from tempfile import TemporaryDirectory

def main():

    parser = argparse.ArgumentParser()

    # good brightness: -0.35
    parser.add_argument("--brightness", "-b",
                        type=str, nargs=1,
                        default="0")
    parser.add_argument("--output", "-o",
                        type=str, nargs=1)
    parser.add_argument("--papersize", "-p",
                        help="Paper size (passed to tiff2pdf)",
                        type=str, nargs=1)
    parser.add_argument("--tempdir", "-t",
                        help="Use this as temporary directory (for debugging)",
                        type=str)
    parser.add_argument("input_file",
                        type=str, nargs="+",
                        help="input filename")
    args = parser.parse_args()

    if args.tempdir is None:
        with TemporaryDirectory() as tempdir:
            process(args, tempdir)
    else:
        process(args, args.tempdir)


def process(args, tempdir):
        
        pages_dir = os.path.join(tempdir, "pages")
        os.mkdir(pages_dir)

        for filename in args.input_file:
            outfile = os.path.join(pages_dir, filename + ".tiff")
            subprocess.call(["econvert",
                             "-i", filename,
                             "--brightness", args.brightness[0],
                             "--colorspace", "bilevel",
                             "--output", outfile])

        tiffcp_args = ["tiffcp", "-c", "g4"]
        tiffcp_args += [os.path.join("pages", f + ".tiff")
                        for f in args.input_file]
        tiffcp_args.append("all.tiff")
        subprocess.call(tiffcp_args, cwd=tempdir)

        tiff2pdf_args = ["tiff2pdf", "-c", "g4", "-x600", "-y600"]
        if args.output is not None:
            tiff2pdf_args += ["-o", args.output[0]]
        if args.papersize is not None:
            tiff2pdf_args += ["-p", args.papersize[0]]
        tiff2pdf_args.append(os.path.join(tempdir, "all.tiff"))
        subprocess.call(tiff2pdf_args)

if __name__ == "__main__":
    main()
