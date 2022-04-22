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

from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brightness", "-b",
                        help="Brightness adjustment (default: 0)",
                        type=str, nargs=1,
                        default="0")
    parser.add_argument("--output", "-o",
                        help="Output filename (required, unless -e supplied)",
                        metavar="FILENAME",
                        type=str, required=False)
    parser.add_argument("--append", "-a",
                        help="Append page(s) to existing PDF output file",
                        action="store_true")
    parser.add_argument("--papersize", "-p",
                        metavar="ISO_NAME",
                        help="Paper size (A4 or A5)",
                        type=str, default="A4")
    parser.add_argument("--tempdir", "-t",
                        help="Use DIRECTORY as temporary directory",
                        metavar="DIRECTORY",
                        type=str)
    parser.add_argument("--rotate", "-r",
                        help="Rotate pages by the given number of degrees",
                        metavar="DEGREES",
                        type=str)
    parser.add_argument("--languages", "-l",
                        help="OCR the PDF in these languages "
                             "(e.g. 'eng+deu')",
                        metavar="ISO_639_2_CODES",
                        type=str)
    parser.add_argument("--scan", "-s",
                        help="Acquire image from scanner (ignores input files)",
                        action="store_true")
    parser.add_argument("--device", "-d",
                        help="Scanner device (implies --scan)",
                        metavar="SANE_DEVICE_NAME",
                        type=str)
    parser.add_argument("--correct-position", "-c",
                        help="Correct positioning of flatbed scans from "
                             "Brother MFC-L2710DW",
                        action="store_true")
    parser.add_argument("--invert", "-i",
                        help="Invert colours",
                        action="store_true")
    parser.add_argument("--export-repositioned", "-e", type=str,
                        metavar="FILENAME",
                        help="Don't convert to bilevel or make a PDF. "
                             "Instead, export first repositioned page to "
                             "specified file.")
    parser.add_argument("--colour", "-C", action="store_true",
                        help="Make initial scan in colour (useful with -e)")
    parser.add_argument("input_files",
                        type=str, nargs="*",
                        help="input filename")
    args = parser.parse_args()

    if not args.input_files and not args.scan and not args.device:
        exit_with_error(": error: the --scan option, the --device option, "
                        " or at least one input file must be supplied.")

    if not args.output and not args.export_repositioned:
        exit_with_error("either --output or --export-repositioned must be"
                        "given.")

    if args.output:
        if args.append:
            if not os.path.isfile(args.output):
                exit_with_error("cannot append, "
                                "since output file does not exist.")
        else:
            if os.path.exists(args.output):
                exit_with_error("output file exists "
                                "(use --append to append to it).")

    if args.tempdir is None:
        with TemporaryDirectory() as tempdir:
            process(args, tempdir)
    else:
        process(args, os.path.abspath(args.tempdir))


def exit_with_error(message: str):
    print(os.path.basename(sys.argv[0]) + ": " + message, file=sys.stderr)
    sys.exit(1)


def process(args, tempdir: str) -> None:
    pages_dir = os.path.join(tempdir, "pages_positioned")
    input_files = scan_document(args, tempdir) if (args.scan or args.device) \
        else args.input_files
    basenames = convert_and_reposition(input_files, args,
                                       pages_dir)
    if args.export_repositioned:
        shutil.copy2(os.path.join(pages_dir, basenames[0] + ".png"),
                     args.export_repositioned)
        return

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
        # NB: mode names are scanner-specific, and a unique prefix
        # apparently suffices to specify the mode.
        "--mode", "24bit Color[Fast]" if args.colour else "True Gray",
        "--format", "tiff",
        "--output-file", os.path.join(tempdir, "scan.tiff")
    ]
    if args.device is not None:
        scanimage_args += ["--device", args.device]

    subprocess.check_call(scanimage_args)
    return [output_file]


def convert_and_reposition(input_files, args, output_dir):
    """Convert input files to PNG and, optionally, reposition content.

    We convert/save to PNG rather than back to TIFF because, for some
    unknown reason, econvert chokes on TIFFs saved by PIL."""
    basenames = []
    os.mkdir(output_dir)
    i = 0

    for input_filename in input_files:
        output_basename = "{:05}".format(i)
        basenames.append(output_basename)
        output_filename = os.path.join(output_dir, output_basename + ".png")
        if args.correct_position:
            reposition(args.papersize.lower(), input_filename, output_filename)
        else:
            subprocess.run(["econvert", "-i", input_filename, "-o",
                            output_filename])
        i += 1
    return basenames


def reposition(paper_size, input_filename, output_filename):
    settings = dict(
        a4=(4912, 6874, 4889, 6874, 4961, 7016, 72, 90),
        a5=(3440, 4911, 3362, 4819, 3496, 4961, 70, 90))
    assert paper_size in settings, "Unknown paper size %s" % paper_size
    in_w, in_h, crop_w, crop_h, out_w, out_h, offset_x, offset_y = \
        settings[paper_size]
    scan = Image.open(input_filename)
    assert scan.size == (in_w, in_h)
    cropped = scan.crop((0, 0, crop_w, crop_h))
    full_size = _new_pil_image(scan.mode, out_w, out_h)
    full_size.paste(cropped, (offset_x, offset_y))
    full_size.save(output_filename)


def _new_pil_image(scan_mode, width, height):
    return Image.new(mode=scan_mode, size=(width, height),
                     color=255 if scan_mode == "L" else (255, 255, 255))


def convert_to_bilevel(args, basenames, pages_bilevel_dir, pages_dir):
    """Convert single-page PNGs to bilevel TIFFs, and optionally rotate"""
    os.mkdir(pages_bilevel_dir)
    for basename in basenames:
        infile = os.path.join(pages_dir, basename + ".png")
        outfile = os.path.join(pages_bilevel_dir, basename + ".tiff")
        econvert_args = ["econvert",
                         "-i", infile,
                         "--brightness", args.brightness[0],
                         "--colorspace", "bilevel"]
        if args.rotate is not None:
            econvert_args += ["--rotate", args.rotate]
        if args.invert:
            econvert_args.append("--negate")
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
        subprocess.check_call([
            "ocrmypdf",
            "--language", languages,
            input_file,
            output_file,
        ])
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
