from flask import make_response
import csv
import io
import json
from fpdf import FPDF

from ..utils import generate_xlsx


def csv_response(symbol: str, headers: list[str], row: list) -> 'Response':
    """Return a CSV file download response for the provided row."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(row)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={symbol}_data.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


def xlsx_response(symbol: str, headers: list[str], row: list) -> 'Response':
    """Return an XLSX file download response for the provided row."""
    output = generate_xlsx(headers, [row])
    response = make_response(output)
    response.headers["Content-Disposition"] = f"attachment; filename={symbol}_data.xlsx"
    response.headers["Content-Type"] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return response


def json_response(symbol: str, data: dict) -> 'Response':
    """Return a JSON download response."""
    response = make_response(json.dumps(data))
    response.headers["Content-Disposition"] = f"attachment; filename={symbol}_data.json"
    response.headers["Content-Type"] = "application/json"
    return response


def pdf_response(symbol: str, fields: list[tuple[str, str]]) -> 'Response':
    """Return a PDF download response with the provided fields."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=f"Stock Data for {symbol}", ln=1)
    for label, value in fields:
        pdf.cell(0, 10, txt=f"{label}: {value}", ln=1)
    pdf_output = pdf.output(dest="S").encode("latin-1")
    response = make_response(pdf_output)
    response.headers["Content-Disposition"] = f"attachment; filename={symbol}_data.pdf"
    response.headers["Content-Type"] = "application/pdf"
    return response
