"""
Document Management with Versioning and Auto-Reindex
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json
import hashlib
from loguru import logger


class DocumentManager:
    """Manage document uploads with versioning"""
    
    def __init__(self, docs_dir: str = "docs", versions_dir: str = "data/versions"):
        self.docs_dir = Path(docs_dir)
        self.versions_dir = Path(versions_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # Load document registry
        self.registry_file = self.versions_dir / "document_registry.json"
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load document registry"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_registry(self):
        """Save document registry"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def upload_document(self, file_content: bytes, filename: str, 
                       uploaded_by: str) -> Dict:
        """
        Upload document with versioning
        Returns: {"status": "new|updated", "version": 1, "needs_reindex": True}
        """
        # Save temporary file to calculate hash
        temp_path = self.docs_dir / f"temp_{filename}"
        with open(temp_path, 'wb') as f:
            f.write(file_content)
        
        file_hash = self._calculate_hash(temp_path)
        
        # Check if document exists
        doc_id = filename
        if doc_id in self.registry:
            # Check if content changed
            if self.registry[doc_id]["current_hash"] == file_hash:
                temp_path.unlink()  # Remove temp file
                return {
                    "status": "unchanged",
                    "version": self.registry[doc_id]["version"],
                    "needs_reindex": False,
                    "message": "Document content unchanged"
                }
            
            # Content changed - create new version
            old_version = self.registry[doc_id]["version"]
            new_version = old_version + 1
            
            # Archive old version
            old_file = self.docs_dir / filename
            archive_name = f"{filename}.v{old_version}"
            archive_path = self.versions_dir / archive_name
            shutil.copy2(old_file, archive_path)
            
            # Update to new version
            shutil.move(str(temp_path), str(old_file))
            
            self.registry[doc_id] = {
                "filename": filename,
                "version": new_version,
                "current_hash": file_hash,
                "uploaded_by": uploaded_by,
                "uploaded_at": datetime.now().isoformat(),
                "previous_versions": self.registry[doc_id].get("previous_versions", []) + [
                    {
                        "version": old_version,
                        "hash": self.registry[doc_id]["current_hash"],
                        "archived_at": datetime.now().isoformat()
                    }
                ]
            }
            
            self._save_registry()
            logger.info(f"Document updated: {filename} (v{old_version} -> v{new_version})")
            
            return {
                "status": "updated",
                "version": new_version,
                "needs_reindex": True,
                "message": f"Document updated from v{old_version} to v{new_version}"
            }
        
        else:
            # New document
            final_path = self.docs_dir / filename
            shutil.move(str(temp_path), str(final_path))
            
            self.registry[doc_id] = {
                "filename": filename,
                "version": 1,
                "current_hash": file_hash,
                "uploaded_by": uploaded_by,
                "uploaded_at": datetime.now().isoformat(),
                "previous_versions": []
            }
            
            self._save_registry()
            logger.info(f"New document uploaded: {filename} (v1)")
            
            return {
                "status": "new",
                "version": 1,
                "needs_reindex": True,
                "message": "New document uploaded"
            }
    
    def delete_document(self, filename: str) -> Dict:
        """Delete document and archive"""
        doc_id = filename
        if doc_id not in self.registry:
            return {"status": "error", "message": "Document not found"}
        
        # Archive current version
        current_file = self.docs_dir / filename
        if current_file.exists():
            version = self.registry[doc_id]["version"]
            archive_name = f"{filename}.v{version}.deleted"
            archive_path = self.versions_dir / archive_name
            shutil.move(str(current_file), str(archive_path))
        
        # Mark as deleted in registry
        self.registry[doc_id]["deleted"] = True
        self.registry[doc_id]["deleted_at"] = datetime.now().isoformat()
        self._save_registry()
        
        logger.info(f"Document deleted: {filename}")
        
        return {
            "status": "deleted",
            "needs_reindex": True,
            "message": f"Document {filename} deleted and archived"
        }
    
    def list_documents(self) -> List[Dict]:
        """List all active documents"""
        docs = []
        for doc_id, info in self.registry.items():
            if not info.get("deleted", False):
                docs.append({
                    "filename": info["filename"],
                    "version": info["version"],
                    "uploaded_by": info["uploaded_by"],
                    "uploaded_at": info["uploaded_at"],
                    "has_versions": len(info.get("previous_versions", [])) > 0
                })
        return docs
    
    def get_document_info(self, filename: str) -> Optional[Dict]:
        """Get document information"""
        doc_id = filename
        if doc_id in self.registry and not self.registry[doc_id].get("deleted", False):
            return self.registry[doc_id]
        return None
