#!/usr/bin/env python3

"""
Convert a series of image files to a multi-page bilevel (i.e. black and
white) PDF.

By Pontus Lurcock, 2017-2020 (pont -at- talvi.net).
Released under the MIT license (see accompanying file LICENSE for details).
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
                        help="Brightness adjustment (default: 0)",
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
    parser.add_argument("--correct-position", "-c",
                        help="Correct positioning for scans from "
                             "Brother MFC-L2710DW",
                        action="store_true")
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
    pages_dir = os.path.join(tempdir, "pages_positioned")
    basenames = reposition(args, pages_dir)
    pages_bilevel_dir = os.path.join(tempdir, "pages_bilevel")
    convert_to_bilevel(args, basenames, pages_bilevel_dir, pages_dir)
    make_multipage_tiff(basenames, pages_bilevel_dir, tempdir)
    tiff2pdf_output_file = convert_tiff_to_pdf(args, tempdir)
    perform_ocr_on_pdf(args, tiff2pdf_output_file)


def reposition(args, pages_dir):
    """Adjust page positions if requested in arguments."""
    basenames = []
    os.mkdir(pages_dir)
    i = 0
    for input_filename in args.input_file:
        output_basename = "{:05}".format(i)
        basenames.append(output_basename)
        output_filename = os.path.join(pages_dir, output_basename + ".tiff")
        if args.correct_position:
            convert_args = [
                "convert", input_filename,
                "-gravity", "southeast", "-chop", "55x0",
                "-gravity", "northwest", "-splice", "72x90",
                "-gravity", "southeast", "-splice", "0x52",
                output_filename
            ]
            subprocess.call(convert_args)
        else:
            shutil.copy2(input_filename, output_filename)
        i += 1
    return basenames


def convert_to_bilevel(args, basenames, pages_bilevel_dir, pages_dir):
    """Convert single-page TIFFs to bilevel colour space."""
    os.mkdir(pages_bilevel_dir)
    for basename in basenames:
        infile = os.path.join(pages_dir, basename + ".tiff")
        outfile = os.path.join(pages_bilevel_dir, basename + ".tiff")
        econvert_args = ["econvert",
                         "-i", infile,
                         "--brightness", args.brightness[0],
                         "--colorspace", "bilevel"]
        if args.rotate is not None:
            econvert_args += ["--rotate", args.rotate]
        econvert_args += ["--output", outfile]
        subprocess.call(econvert_args)


def make_multipage_tiff(basenames, pages_bilevel_dir, tempdir):
    """Combine single-page TIFFs into a multi-page TIFF."""
    tiffcp_args = ["tiffcp", "-c", "g4"]
    tiffcp_args += [os.path.join(pages_bilevel_dir, basename + ".tiff")
                    for basename in basenames]
    tiffcp_args.append("all.tiff")
    subprocess.call(tiffcp_args, cwd=tempdir)


def convert_tiff_to_pdf(args, tempdir):
    """Convert multi-page TIFF to PDF."""
    tiff2pdf_output_file = os.path.join(tempdir, "all.pdf")
    tiff2pdf_args = ["tiff2pdf", "-c", "g4", "-x600", "-y600"]
    tiff2pdf_args += ["-o", tiff2pdf_output_file]
    if args.papersize is not None:
        tiff2pdf_args += ["-p", args.papersize[0]]
    tiff2pdf_args.append(os.path.join(tempdir, "all.tiff"))
    subprocess.call(tiff2pdf_args)
    return tiff2pdf_output_file


def perform_ocr_on_pdf(args, tiff2pdf_output_file):
    """Perform OCR on the PDF, if requested in arguments."""
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
