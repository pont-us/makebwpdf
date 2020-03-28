#!/usr/bin/env python3

"""
Convert a series of image files to a multi-page bilevel (i.e. black and
white) PDF.

Requires: econvert (from https://exactcode.com/opensource/exactimage/ ),
tiffcp, tiff2pdf, pdfsandwich.

By Pontus Lurcock, 2017-2020 (pont -at- talvi.net).
Released into the public domain.
"""

import argparse
import os
import os.path
import subprocess
import shutil
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brightness", "-b",
                        type=str, nargs=1,
                        default="0")
    parser.add_argument("--output", "-o",
                        help="Output filename (required)",
                        type=str, nargs=1, required=True)
    parser.add_argument("--papersize", "-p",
                        help="Paper size (passed to tiff2pdf)",
                        type=str, nargs=1)
    parser.add_argument("--tempdir", "-t",
                        help="Use TEMPDIR as temporary directory",
                        type=str)
    parser.add_argument("--rotate", "-r",
                        help="Rotate pages by the given number of degrees",
                        type=str)
    parser.add_argument("--languages", "-l",
                        help="OCR the scan in these languages "
                             "(e.g. 'eng+deu')",
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
        econvert_args = ["econvert",
                         "-i", filename,
                         "--brightness", args.brightness[0],
                         "--colorspace", "bilevel"]
        if args.rotate is not None:
            econvert_args += ["--rotate", args.rotate]
        econvert_args += ["--output", outfile]
        subprocess.call(econvert_args)

    tiffcp_args = ["tiffcp", "-c", "g4"]
    tiffcp_args += [os.path.join("pages", f + ".tiff")
                    for f in args.input_file]
    tiffcp_args.append("all.tiff")
    subprocess.call(tiffcp_args, cwd=tempdir)

    tiff2pdf_output_file = os.path.join(tempdir, "all.pdf")
    tiff2pdf_args = ["tiff2pdf", "-c", "g4", "-x600", "-y600"]
    tiff2pdf_args += ["-o", tiff2pdf_output_file]
    if args.papersize is not None:
        tiff2pdf_args += ["-p", args.papersize[0]]
    tiff2pdf_args.append(os.path.join(tempdir, "all.tiff"))
    subprocess.call(tiff2pdf_args)

    if args.languages is not None:
        pdfsandwich_args = [
            "pdfsandwich",
            "-maxpixels", "999999999",
            "-lang", args.languages,
            "-o", args.output[0],
            "-nopreproc",
            tiff2pdf_output_file
        ]
        subprocess.call(pdfsandwich_args)
    else:
        shutil.copy2(tiff2pdf_output_file, args.output[0])


if __name__ == "__main__":
    main()
