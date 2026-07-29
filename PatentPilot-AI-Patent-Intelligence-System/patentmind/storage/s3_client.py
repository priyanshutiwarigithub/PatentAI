import os
import time
import io
import boto3
from botocore.exceptions import ClientError
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()

class S3StorageClient:
    def __init__(self):
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "patentmind-patent-storage")
        
        self.local_storage_dir = os.path.join(os.path.expanduser("~"), ".patentmind_s3_mock")
        os.makedirs(self.local_storage_dir, exist_ok=True)

        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.region
            )
            self.mock_mode = False
        except Exception as e:
            console.print(f"[yellow]S3 Client fallback to local storage mock: {e}[/yellow]")
            self.mock_mode = True

    def upload_patent_pdf(self, patent_number: str, file_bytes: bytes) -> str:
        s3_key = f"patents/{patent_number}.pdf"
        retries = 3
        backoff = 1.0

        for attempt in range(1, retries + 1):
            try:
                if not self.mock_mode:
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        Body=file_bytes,
                        ContentType="application/pdf"
                    )
                    console.print(f"[bold green]S3 Upload Success:[/bold green] {s3_key}")
                    return s3_key
                else:
                    raise ClientError({"Error": {"Code": "MockMode"}}, "put_object")
            except ClientError as ce:
                err_code = ce.response.get("Error", {}).get("Code", "")
                if err_code in ["InvalidAccessKeyId", "SignatureDoesNotMatch", "MockMode", "AuthFailure"]:
                    console.print(f"[yellow]AWS credentials placeholder detected ({err_code}). Using local mock S3 storage.[/yellow]")
                    self.mock_mode = True
                    local_path = os.path.join(self.local_storage_dir, f"{patent_number}.pdf")
                    with open(local_path, "wb") as f:
                        f.write(file_bytes)
                    return f"local://patents/{patent_number}.pdf"
                if attempt == retries:
                    local_path = os.path.join(self.local_storage_dir, f"{patent_number}.pdf")
                    with open(local_path, "wb") as f:
                        f.write(file_bytes)
                    return f"local://patents/{patent_number}.pdf"
                time.sleep(backoff)
                backoff *= 2.0

        return s3_key

    def download_patent_pdf(self, s3_key: str) -> bytes:
        if s3_key.startswith("local://"):
            patent_filename = s3_key.replace("local://patents/", "")
            local_path = os.path.join(self.local_storage_dir, patent_filename)
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    return f.read()
            return b""

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response["Body"].read()
        except Exception as e:
            console.print(f"[bold red]S3 Download Failed for {s3_key}: {e}[/bold red]")
            return b""

    def check_exists(self, s3_key: str) -> bool:
        if s3_key.startswith("local://"):
            patent_filename = s3_key.replace("local://patents/", "")
            local_path = os.path.join(self.local_storage_dir, patent_filename)
            return os.path.exists(local_path)

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

s3_client = S3StorageClient()
