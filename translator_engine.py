import pymupdf as fitz
import os
import logging
from typing import Callable, Optional
from font_manager import font_manager
from translation_service import translation_service

logger = logging.getLogger("translator_engine")
logger.setLevel(logging.INFO)

_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            logger.info("RapidOCR engine initialized for scanned PDF support.")
        except Exception as e:
            logger.warning(f"Could not initialize RapidOCR: {e}")
            _ocr_engine = False
    return _ocr_engine if _ocr_engine is not False else None

from PIL import Image
import numpy as np

def process_pdf_document(
    pdf_bytes: bytes,
    target_lang: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> bytes:
    """
    Parses PDF, extracts text blocks with bboxes (x0, y0, x1, y1), translates text,
    redacts original text while preserving images/tables, auto-scales font size,
    and renders translated text using Unicode Noto fonts. Supports scanned image PDFs via OCR.
    """
    if not pdf_bytes or len(pdf_bytes) == 0:
        raise ValueError("Provided PDF file is empty.")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Corrupted or invalid PDF file: {str(e)}")

    total_pages = len(doc)
    if total_pages == 0:
        raise ValueError("PDF document has no pages.")

    # Get target font path & alias
    font_path, font_alias = font_manager.get_font_for_language(target_lang)

    total_blocks_found = 0

    for page_num in range(total_pages):
        page = doc[page_num]
        
        if progress_callback:
            progress_callback(page_num + 1, total_pages, f"Translating page {page_num + 1} of {total_pages}...")

        # Extract structured block layout
        text_page = page.get_text("dict")
        blocks = text_page.get("blocks", [])

        blocks_to_process = []
        for b in blocks:
            if b.get("type") == 0: # Type 0 = Text block
                bbox = fitz.Rect(b["bbox"])
                
                # Filter out tiny or invalid boxes
                if bbox.width < 5 or bbox.height < 5:
                    continue

                lines_text = []
                font_sizes = []
                colors = []

                for line in b.get("lines", []):
                    line_spans_text = []
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if span_text.strip():
                            line_spans_text.append(span_text)
                            font_sizes.append(span.get("size", 10.0))
                            
                            # Convert integer color to RGB float tuple
                            c_int = span.get("color", 0)
                            r = ((c_int >> 16) & 255) / 255.0
                            g = ((c_int >> 8) & 255) / 255.0
                            b_val = (c_int & 255) / 255.0
                            colors.append((r, g, b_val))
                    
                    if line_spans_text:
                        lines_text.append(" ".join(line_spans_text))

                full_text = "\n".join(lines_text).strip()

                if full_text:
                    avg_size = sum(font_sizes) / len(font_sizes) if font_sizes else 10.0
                    main_color = colors[0] if colors else (0, 0, 0)
                    blocks_to_process.append({
                        "bbox": bbox,
                        "original_text": full_text,
                        "font_size": avg_size,
                        "color": main_color
                    })

        if not blocks_to_process:
            # Fallback 1: Try get_text("blocks")
            try:
                raw_blocks = page.get_text("blocks")
                for rb in raw_blocks:
                    if len(rb) >= 7 and rb[6] == 0:
                        bbox = fitz.Rect(rb[0], rb[1], rb[2], rb[3])
                        txt = rb[4].strip()
                        if txt and bbox.width >= 3 and bbox.height >= 3:
                            blocks_to_process.append({
                                "bbox": bbox,
                                "original_text": txt,
                                "font_size": 10.0,
                                "color": (0, 0, 0)
                            })
            except Exception as ex:
                logger.debug(f"Fallback get_text('blocks') exception on page {page_num+1}: {ex}")

        if not blocks_to_process:
            # Fallback 2: Perform RapidOCR for scanned/image PDFs
            ocr = get_ocr_engine()
            if ocr:
                try:
                    pix_page = page.get_pixmap(dpi=150)
                    scale_x = page.rect.width / pix_page.width
                    scale_y = page.rect.height / pix_page.height

                    img_pil = Image.open(fitz.io.BytesIO(pix_page.tobytes("png")))
                    img_np = np.array(img_pil)

                    ocr_res, _ = ocr(img_np)
                    if ocr_res:
                        for item in ocr_res:
                            box, text, score = item
                            try:
                                score_val = float(score)
                            except (ValueError, TypeError):
                                score_val = 1.0

                            if not text.strip() or score_val < 0.3:
                                continue

                            xs = [pt[0] * scale_x for pt in box]
                            ys = [pt[1] * scale_y for pt in box]
                            rect = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
                            font_size = max(8.0, rect.height * 0.75)

                            blocks_to_process.append({
                                "bbox": rect,
                                "original_text": text.strip(),
                                "font_size": font_size,
                                "color": (0, 0, 0)
                            })
                except Exception as ex:
                    logger.warning(f"RapidOCR exception on page {page_num+1}: {ex}")

        if not blocks_to_process:
            logger.info(f"Page {page_num+1} has no text blocks. Preserving layout.")
            continue

        total_blocks_found += len(blocks_to_process)

        # Step 1: Translate text for all blocks on this page in a single batch API call
        orig_texts = [item["original_text"] for item in blocks_to_process]
        translated_texts = translation_service.translate_batch(
            orig_texts,
            target_lang=target_lang
        )

        for item, trans_text in zip(blocks_to_process, translated_texts):
            item["translated_text"] = trans_text

        # Step 2: Redact original text locations (keeping graphics/images intact)
        for item in blocks_to_process:
            page.add_redact_annot(item["bbox"], fill=(1, 1, 1)) # White background

        # Apply redactions preserving images/lines
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # Step 3: Register Unicode font once per page
        if font_path and os.path.exists(font_path):
            try:
                page.insert_font(fontname=font_alias, fontfile=font_path)
            except Exception:
                pass

        # Re-insert translated text with auto-scaling font size & Unicode font
        for item in blocks_to_process:
            bbox = item["bbox"]
            text = item["translated_text"]
            orig_size = item["font_size"]
            color = item["color"]

            current_fontsize = orig_size
            min_fontsize = 5.0
            step = 0.5
            
            fit_success = False
            while current_fontsize >= min_fontsize:
                try:
                    res = page.insert_textbox(
                        bbox,
                        text,
                        fontsize=current_fontsize,
                        fontname=font_alias if font_path else "helv",
                        fontfile=font_path,
                        color=color,
                        align=0
                    )
                    if res >= 0:
                        fit_success = True
                        break
                except Exception as ex:
                    logger.debug(f"Font fit trial exception at size {current_fontsize}: {ex}")
                
                current_fontsize -= step

            if not fit_success:
                try:
                    page.insert_textbox(
                        bbox,
                        text,
                        fontsize=min_fontsize,
                        fontname=font_alias if font_path else "helv",
                        fontfile=font_path,
                        color=color,
                        align=0
                    )
                except Exception as ex:
                    logger.warning(f"Failed to insert text in block {bbox}: {ex}")

    if total_blocks_found == 0:
        raise ValueError("No selectable text blocks were found in this PDF document. This usually happens if the PDF is a scanned paper document, photo, or image-only file. Please try uploading a digital PDF with selectable text.")

    output_pdf_bytes = doc.tobytes()
    doc.close()
    
    if progress_callback:
        progress_callback(total_pages, total_pages, "Translation complete!")

    return output_pdf_bytes
