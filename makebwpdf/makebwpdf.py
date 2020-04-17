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
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brightness", "-b",
                        help="Brightness adjustment (default: 0)",
                        type=str, nargs=1,
                        default="0")
    parser.add_argument("--output", "-o",
                        help="Output filename (required)",
                        type=str, required=True)
    parser.add_argument("--append", "-a",
                        help="Append page(s) to existing PDF output file",
                        action="store_true")
    parser.add_argument("--papersize", "-p",
                        help="Paper size",
                        type=str, default="A4")
    parser.add_argument("--tempdir", "-t",
                        help="Use TEMPDIR as temporary directory",
                        type=str)
    parser.add_argument("--rotate", "-r",
                        help="Rotate pages by the given number of degrees",
                        type=str)
    parser.add_argument("--languages", "-l",
                        help="OCR the PDF in these languages "
                             "(e.g. 'eng+deu')",
                        type=str)
    parser.add_argument("--scan", "-s",
                        help="Acquire image from scanner (ignores input files)",
                        action="store_true")
    parser.add_argument("--correct-position", "-c",
                        help="Correct positioning for scans from "
                             "Brother MFC-L2710DW",
                        action="store_true")
    parser.add_argument("input_files",
                        type=str, nargs="*",
                        help="input filename")
    args = parser.parse_args()

    if not args.input_files and not args.scan:
        exit_with_error(": error: either the --scan option or at least "
                        "one input file must be supplied.")

    if args.append:
        if not os.path.isfile(args.output):
            exit_with_error("cannot append, since output file does not exist")
    else:
        if os.path.exists(args.output):
            exit_with_error("output file exists "
                            "(use --append to append to it)")

    if args.tempdir is None:
        with TemporaryDirectory() as tempdir:
            process(args, tempdir)
    else:
        process(args, os.path.abspath(args.tempdir))


def exit_with_error(message):
    print(os.path.basename(sys.argv[0]) + ": " + message, file=sys.stderr)
    sys.exit(1)


def process(args, tempdir):
    pages_dir = os.path.join(tempdir, "pages_positioned")
    input_files = scan_document(args, tempdir) if args.scan \
        else args.input_files
    basenames = copy_and_reposition(input_files, args,
                                    pages_dir)
    pages_bilevel_dir = os.path.join(tempdir, "pages_bilevel")
    convert_to_bilevel(args, basenames, pages_bilevel_dir, pages_dir)
    make_multipage_tiff(basenames, pages_bilevel_dir, tempdir)
    tiff2pdf_output_file = convert_tiff_to_pdf(args, tempdir)
    ocr_output_file = os.path.join(tempdir, "all_ocr.pdf")
    perform_ocr_on_pdf(args.languages, tiff2pdf_output_file, ocr_output_file)
    if args.append:
        append_pdf(args.output, ocr_output_file, tempdir)
    else:
        shutil.copy2(ocr_output_file, args.output)


def scan_document(args, tempdir):
    """Acquire image from scanner."""

    output_file = os.path.join(tempdir, "scan.tiff")
    
    # Unless A5 explicitly specified, we assume A4.
    size = (148, 210) if args.papersize.lower() == "a5" else (210, 297)
    
    scanimage_args = [
        "scanimage",
        "-x", str(size[0]),
        "-y", str(size[1]),
        "--resolution", "600",
        "--mode", "True Gray",
        "--format", "tiff",
        "--output-file", os.path.join(tempdir, "scan.tiff")
    ]
    subprocess.check_call(scanimage_args)
    return [output_file]


def copy_and_reposition(input_files, args, output_dir):
    """Copy input files and, optionally, reposition content."""
    basenames = []
    os.mkdir(output_dir)
    i = 0

    a4_args = """
    -gravity southeast -chop 55x0 
    -gravity northwest -splice 72x90 
    -gravity southeast -splice 0x52 
    """.split()

    a5_args = """
    -gravity southeast -chop 78x0
    -gravity northwest -splice 70x90
    -gravity southeast -chop 0x92
    """.split()

    convert_args = a5_args if args.papersize.lower() == "a5" else a4_args
    
    for input_filename in input_files:
        output_basename = "{:05}".format(i)
        basenames.append(output_basename)
        output_filename = os.path.join(output_dir, output_basename + ".tiff")
        if args.correct_position:
            subprocess.check_call(["convert", input_filename ]
                                  + convert_args
                                  + [output_filename])
        else:
            shutil.copy2(input_filename, output_filename)
        i += 1
    return basenames


def convert_to_bilevel(args, basenames, pages_bilevel_dir, pages_dir):
    """Convert single-page TIFFs to bilevel, and optionally rotate"""
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
        subprocess.check_call(econvert_args)


def make_multipage_tiff(basenames, pages_bilevel_dir, tempdir):
    """Combine single-page TIFFs into a multi-page TIFF."""
    tiffcp_args = ["tiffcp", "-c", "g4"]
    tiffcp_args += [os.path.join(pages_bilevel_dir, basename + ".tiff")
                    for basename in basenames]
    tiffcp_args.append("all.tiff")
    subprocess.check_call(tiffcp_args, cwd=tempdir)


def convert_tiff_to_pdf(args, tempdir):
    """Convert multi-page TIFF to PDF."""
    tiff2pdf_output_file = os.path.join(tempdir, "all.pdf")
    tiff2pdf_args = ["tiff2pdf", "-c", "g4", "-x600", "-y600"]
    tiff2pdf_args += ["-o", tiff2pdf_output_file]
    tiff2pdf_args.append(os.path.join(tempdir, "all.tiff"))
    subprocess.check_call(tiff2pdf_args)
    return tiff2pdf_output_file


def perform_ocr_on_pdf(languages, input_file, output_file):
    """Perform OCR on the PDF, if requested in arguments."""
    if languages is not None:
        pdfsandwich_args = [
            "pdfsandwich",
            "-maxpixels", "999999999",
            "-resolution", "600",
            "-lang", languages,
            "-o", output_file,
            "-nopreproc",
            input_file
        ]
        subprocess.check_call(pdfsandwich_args)
    else:
        shutil.copy2(input_file, output_file)


def append_pdf(main_file, additional_file, tempdir):
    output_file = os.path.join(tempdir, "appended.pdf")
    pdftk_args = [
        "pdftk", main_file, additional_file,
        "cat",
        "output", output_file
    ]
    subprocess.check_call(pdftk_args)
    shutil.copy2(output_file, main_file)


if __name__ == "__main__":
    main()
