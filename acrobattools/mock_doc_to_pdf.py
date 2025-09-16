import os
import logging
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.create_pdf_job import CreatePDFJob
from adobe.pdfservices.operation.pdfjobs.jobs.extract_pdf_job import ExtractPDFJob
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_element_type import ExtractElementType
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_pdf_params import ExtractPDFParams
from adobe.pdfservices.operation.pdfjobs.result.create_pdf_result import CreatePDFResult
from adobe.pdfservices.operation.pdfjobs.result.extract_pdf_result import ExtractPDFResult
from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
from adobe.pdfservices.operation.io.stream_asset import StreamAsset
# Initialize the logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_pdf_service_credentials():
    """
    Retrieves credentials from environment variables.

    Raises:
        ValueError: If required environment variables are not set.
    """
    client_id = os.getenv('PDF_SERVICES_CLIENT_ID')
    client_secret = os.getenv('PDF_SERVICES_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise ValueError("PDF_SERVICES_CLIENT_ID and PDF_SERVICES_CLIENT_SECRET environment variables must be set.")
    return ServicePrincipalCredentials(client_id, client_secret)


# Your provided extraction class
class ExtractTextTableInfoFromPDF:
    def __init__(self, input_pdf_path: str, output_zip_path: str):
        self.input_pdf_path = input_pdf_path
        self.output_zip_path = output_zip_path

    def extract(self):
        try:
            # Read input PDF file as bytes
            with open(self.input_pdf_path, 'rb') as file:
                input_stream = file.read()

            # Create credentials from environment variables
            credentials = get_pdf_service_credentials()
            pdf_services = PDFServices(credentials=credentials)

            # Upload the PDF file as an asset
            input_asset = pdf_services.upload(input_stream=input_stream, mime_type=PDFServicesMediaType.PDF)

            # Define extraction parameters: extract text and tables_ecrf
            extract_pdf_params = ExtractPDFParams(
                elements_to_extract=[ExtractElementType.TEXT, ExtractElementType.TABLES]
            )

            # Create extraction job
            extract_pdf_job = ExtractPDFJob(input_asset=input_asset, extract_pdf_params=extract_pdf_params)

            # Submit the job and get the result location
            location = pdf_services.submit(extract_pdf_job)

            # Retrieve the job result
            pdf_services_response = pdf_services.get_job_result(location, ExtractPDFResult)

            # Get the resulting asset (ZIP file with extracted data)
            result_asset: CloudAsset = pdf_services_response.get_result().get_resource()

            # Get the content stream of the result asset
            stream_asset: StreamAsset = pdf_services.get_content(result_asset)

            # Write the extracted data ZIP to output file
            with open(self.output_zip_path, "wb") as output_file:
                output_file.write(stream_asset.get_input_stream())

            logging.info(f"Extraction successful. Output saved to: {self.output_zip_path}")

        except (ServiceApiException, ServiceUsageException, SdkException, ValueError) as e:
            logging.error(f"Exception encountered during extraction: {e}", exc_info=True)
        except FileNotFoundError:
            logging.error(f"Input PDF file not found: {self.input_pdf_path}", exc_info=True)
        except Exception as e:
            logging.error(f"Unexpected error during extraction: {e}", exc_info=True)


#block to convert docx to pdf
def convert_docx_to_pdf(input_docx_path: str, output_pdf_path: str):
    """
    Converts a DOCX file to a PDF using Adobe PDF Services API.

    Returns:
        bool: True if conversion is successful, False otherwise.
    """
    try:
        credentials = get_pdf_service_credentials()
        pdf_services = PDFServices(credentials)

        logging.info(f"Attempting to convert DOCX file to PDF: {input_docx_path}")
        with open(input_docx_path, 'rb') as file:
            input_docx_asset = pdf_services.upload(file, mime_type=PDFServicesMediaType.DOCX)

        create_pdf_job = CreatePDFJob(input_docx_asset)
        location_pdf = pdf_services.submit(create_pdf_job)
        pdf_services_response_pdf = pdf_services.get_job_result(location_pdf, CreatePDFResult)

        # CORRECTED LINE
        # Access the content stream directly from the CreatePDFResult object.
        stream_pdf_asset = pdf_services_response_pdf.get_result().get_input_stream()

        with open(output_pdf_path, "wb") as file:
            file.write(stream_pdf_asset)
        logging.info(f"Successfully converted DOCX to PDF. Output saved to: {output_pdf_path}")
        return True

    except (ServiceApiException, ServiceUsageException, SdkException, ValueError) as e:
        logging.error(f"Exception encountered during conversion: {e}", exc_info=True)
        return False
    except FileNotFoundError:
        logging.error(f"Input DOCX file not found: {input_docx_path}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"Unexpected error during conversion: {e}", exc_info=True)
        return False


# Your existing code with the corrected function should now work correctly.


if __name__ == "__main__":
    # --- Make sure these paths are correct ---
    INPUT_DOCX = '/home/ibab/Desktop/NovoNordisk/Documents_09Sep25/Mock CRF.docx'
    OUTPUT_PDF = 'Mock_CRF_converted.pdf'
    OUTPUT_ZIP = 'Mock_CRF_extracted_data.zip'

    # Step 1: Convert the DOCX to PDF
    conversion_successful = convert_docx_to_pdf(INPUT_DOCX, OUTPUT_PDF)

    # Step 2: Extract data from the newly created PDF
    if conversion_successful:
        extractor = ExtractTextTableInfoFromPDF(OUTPUT_PDF, OUTPUT_ZIP)
        extractor.extract()