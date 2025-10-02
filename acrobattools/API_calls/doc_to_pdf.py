import os
import logging
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.create_pdf_job import CreatePDFJob
from adobe.pdfservices.operation.pdfjobs.result.create_pdf_result import CreatePDFResult

logging.basicConfig(level=logging.INFO)


def convert_doc_to_pdf(input_doc_path, output_pdf_path):
    """
    Convert a document (Word, Excel, PowerPoint) to PDF using Adobe PDF Services API.
    """
    try:
        # Load credentials from environment variables
        client_id = os.getenv("PDF_SERVICES_CLIENT_ID")
        client_secret = os.getenv("PDF_SERVICES_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("PDF_SERVICES_CLIENT_ID and PDF_SERVICES_CLIENT_SECRET environment variables must be set.")

        # Create credentials
        credentials = ServicePrincipalCredentials(client_id, client_secret)

        # Create PDF Services instance
        pdf_services = PDFServices(credentials)

        # Determine media type based on file extension
        file_extension = os.path.splitext(input_doc_path)[1].lower()

        if file_extension == '.docx':
            media_type = PDFServicesMediaType.DOCX
        elif file_extension == '.doc':
            media_type = PDFServicesMediaType.DOC
        elif file_extension == '.xlsx':
            media_type = PDFServicesMediaType.XLSX
        elif file_extension == '.xls':
            media_type = PDFServicesMediaType.XLS
        elif file_extension == '.pptx':
            media_type = PDFServicesMediaType.PPTX
        elif file_extension == '.ppt':
            media_type = PDFServicesMediaType.PPT
        elif file_extension == '.txt':
            media_type = PDFServicesMediaType.TXT
        elif file_extension == '.rtf':
            media_type = PDFServicesMediaType.RTF
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Upload the input document
        logging.info(f"Uploading {input_doc_path}...")
        with open(input_doc_path, 'rb') as file:
            input_asset = pdf_services.upload(file, media_type)

        # Create PDF job
        create_pdf_job = CreatePDFJob(input_asset)

        # Submit job and get result
        logging.info("Creating PDF...")
        location = pdf_services.submit(create_pdf_job)
        pdf_services_response = pdf_services.get_job_result(location, CreatePDFResult)

        # Get result asset
        result_asset = pdf_services_response.get_result().get_asset()

        # Download and save the result
        logging.info(f"Saving PDF to {output_pdf_path}...")
        stream_asset = pdf_services.get_content(result_asset)

        with open(output_pdf_path, "wb") as file:
            file.write(stream_asset.get_input_stream())

        logging.info(f"Successfully created PDF: {output_pdf_path}")
        return True

    except (ServiceApiException, ServiceUsageException, SdkException) as e:
        logging.error(f"Adobe PDF Services error: {e}")
        return False
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False


if __name__ == "__main__":
    # Set your credentials
    os.environ["PDF_SERVICES_CLIENT_ID"] = "aa40bdd8077047138b178685e7b5136e"
    os.environ["PDF_SERVICES_CLIENT_SECRET"] = "p8e-k4Y6mGmZsjbn9EMzxEt-ga0Bwwhc1Y55"

    import sys

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    convert_doc_to_pdf(input_path, output_path)
    success = convert_doc_to_pdf(input_path, output_path)

    if success:
        print("✅ Document conversion completed successfully!")
    else:
        print("❌ Document conversion failed!")
