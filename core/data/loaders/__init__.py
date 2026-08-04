from data.loaders.pdf_loader import PDFLoader
from data.loaders.html_loader import HTMLLoader
from data.loaders.json_loader import JSONLoader
from data.loaders.csv_loader import CSVLoader
from data.loaders.xlsx_loader import XLSXLoader
from data.loaders.markdown_loader import MarkdownLoader
from data.loaders.txt_loader import TXTLoader
from data.loaders.image_loader import ImageLoader
from data.loaders.remote_loader import RemoteLoader

__all__ = [
    "PDFLoader",
    "HTMLLoader",
    "JSONLoader",
    "CSVLoader",
    "XLSXLoader",
    "MarkdownLoader",
    "TXTLoader",
    "ImageLoader",
    "RemoteLoader",
]
