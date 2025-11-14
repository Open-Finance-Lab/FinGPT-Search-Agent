"""
pdf upload endpoint for pageindex integration
allows users to upload pdfs directly to the server
"""

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import os
import hashlib
from pathlib import Path
import logging
import PyPDF2

logger = logging.getLogger(__name__)

# upload directory
UPLOAD_DIR = Path(__file__).parent.parent / "uploads" / "pdfs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_pdf_page_count(file_path):
    """Get the number of pages in a PDF"""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return len(reader.pages)
    except Exception as e:
        logger.warning(f"Could not get page count: {e}")
        return None


@method_decorator(csrf_exempt, name='dispatch')
class PDFUploadView(View):
    """handle pdf file uploads"""
    
    def post(self, request):
        """
        upload a pdf file
        
        expects multipart/form-data with 'pdf' file field
        optional 'description' field
        """
        try:
            # check for file
            if 'pdf' not in request.FILES:
                return JsonResponse({
                    'error': 'no pdf file provided',
                    'detail': 'send file in "pdf" field'
                }, status=400)
            
            pdf_file = request.FILES['pdf']
            description = request.POST.get('description', '')
            
            # validate file type
            if not pdf_file.name.lower().endswith('.pdf'):
                return JsonResponse({
                    'error': 'invalid file type',
                    'detail': 'only .pdf files allowed'
                }, status=400)
            
            # limit file size (50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if pdf_file.size > max_size:
                return JsonResponse({
                    'error': 'file too large',
                    'detail': f'max size is 50MB, got {pdf_file.size / 1024 / 1024:.1f}MB'
                }, status=400)
            
            # generate unique filename
            file_hash = hashlib.md5(pdf_file.read()).hexdigest()[:12]
            pdf_file.seek(0)  # reset file pointer
            
            # keep original name but add hash for uniqueness
            original_name = Path(pdf_file.name).stem
            safe_name = "".join(c for c in original_name if c.isalnum() or c in "._- ")
            filename = f"{safe_name}_{file_hash}.pdf"
            
            # save file
            file_path = UPLOAD_DIR / filename
            with open(file_path, 'wb') as f:
                for chunk in pdf_file.chunks():
                    f.write(chunk)
            
            # get page count
            page_count = get_pdf_page_count(file_path)
            
            logger.info(f"uploaded pdf: {filename} ({pdf_file.size / 1024:.1f}KB, {page_count} pages)")
            
            return JsonResponse({
                'success': True,
                'file_id': file_hash,
                'filename': filename,
                'original_name': pdf_file.name,
                'path': str(file_path),
                'size_kb': round(pdf_file.size / 1024, 1),
                'pages': page_count,
                'description': description
            })
        
        except Exception as e:
            logger.error(f"pdf upload error: {e}")
            return JsonResponse({
                'error': 'upload failed',
                'detail': str(e)
            }, status=500)
    
    def get(self, request):
        """list uploaded pdfs"""
        try:
            pdfs = []
            for pdf_path in UPLOAD_DIR.glob("*.pdf"):
                pdfs.append({
                    'filename': pdf_path.name,
                    'path': str(pdf_path),
                    'size_kb': round(pdf_path.stat().st_size / 1024, 1),
                    'uploaded_at': pdf_path.stat().st_mtime
                })
            
            # sort by upload time (newest first)
            pdfs.sort(key=lambda x: x['uploaded_at'], reverse=True)
            
            return JsonResponse({
                'success': True,
                'count': len(pdfs),
                'pdfs': pdfs
            })
        
        except Exception as e:
            logger.error(f"error listing pdfs: {e}")
            return JsonResponse({
                'error': 'failed to list pdfs',
                'detail': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PDFDeleteView(View):
    """delete an uploaded pdf"""
    
    def delete(self, request, file_id):
        """delete a pdf by its id"""
        try:
            # find file with this id
            for pdf_path in UPLOAD_DIR.glob(f"*_{file_id}.pdf"):
                pdf_path.unlink()
                logger.info(f"deleted pdf: {pdf_path.name}")
                return JsonResponse({
                    'success': True,
                    'message': f'deleted {pdf_path.name}'
                })
            
            return JsonResponse({
                'error': 'file not found',
                'detail': f'no pdf found with id {file_id}'
            }, status=404)
        
        except Exception as e:
            logger.error(f"error deleting pdf: {e}")
            return JsonResponse({
                'error': 'delete failed',
                'detail': str(e)
            }, status=500)

