import fitz
from pathlib import Path
from loguru import logger
from schemas.document_schema import Figure

class FigureExtractor:
    """Extract all embedded images/figures from a PDF and save them."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_figures(self, fitz_doc: fitz.Document, doc_id: str) -> list:
        figures = []
        figure_count = 0

        for page_num, page in enumerate(fitz_doc):
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                try:
                    base_image = fitz_doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    ext = base_image["ext"]

                    if base_image["width"] < 50 or base_image["height"] < 50:
                        continue  # Skip tiny images (icons, watermarks)

                    figure_count += 1
                    filename = f"{doc_id}_fig_{figure_count}.{ext}"
                    save_path = self.output_dir / filename
                    
                    with open(save_path, "wb") as f:
                        f.write(img_bytes)

                    figures.append(Figure(
                        figure_id=f"{doc_id}_fig_{figure_count}",
                        image_path=str(save_path),
                        page_number=page_num + 1,
                    ))
                    
                    logger.debug(f"Extracted figure {figure_count} from page {page_num+1}")
                except Exception as e:
                    logger.warning(f"Failed to extract image xref={xref}: {e}")

        logger.info(f"Extracted {len(figures)} figures total")
        return figures