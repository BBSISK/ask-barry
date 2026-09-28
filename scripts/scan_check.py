"""Try "Scan a job ad" on a photo from your computer, before using it on the live site.

    python -m scripts.scan_check photo.jpg      # prints the text the model read (needs AZURE_* in .env)
"""
import sys
from pathlib import Path


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.exit("Usage: python -m scripts.scan_check photo.jpg")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from app.answering import azure_configured
    from app.scan import ScanError, transcriber_from_env
    if not azure_configured():
        sys.exit("Azure settings missing in .env (run python -m scripts.check_azure)")
    try:
        print(transcriber_from_env()(Path(argv[0]).read_bytes()))
    except ScanError as err:
        sys.exit(str(err))


if __name__ == "__main__":
    main()
