# core/models.py
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, TIMESTAMP, Integer, DECIMAL, JSON, BIGINT, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.core.database import Base

# ================= USERS ===================
class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_active = Column(TIMESTAMP, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# ================= PROJECTS ===================
class Project(Base):
    __tablename__ = "projects"
    project_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_name = Column(String(255))
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)
    status = Column(String(50), default="active")  # active, archived, deleted
    user = relationship("User", backref="projects")

# ================= RFP DOCUMENTS ===================
class RFPDocument(Base):
    __tablename__ = "rfp_documents"
    rfp_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(Text, nullable=False)
    file_size = Column(BIGINT)
    file_hash = Column(String(64))
    uploaded_at = Column(TIMESTAMP, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    processing_started_at = Column(TIMESTAMP)
    processing_completed_at = Column(TIMESTAMP)
    processing_error = Column(Text)
    meta_info = Column(JSON)  # بدل metadata
    project = relationship("Project", backref="rfp_documents")
    user = relationship("User", backref="rfp_documents")

# ================= VENDOR DOCUMENTS ===================
class VendorDocument(Base):
    __tablename__ = "vendor_documents"
    vendor_doc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    vendor_name = Column(String(255), nullable=False)
    rfp_id = Column(UUID(as_uuid=True), ForeignKey("rfp_documents.rfp_id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(Text, nullable=False)
    file_size = Column(BIGINT)
    file_hash = Column(String(64))
    uploaded_at = Column(TIMESTAMP, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    processing_started_at = Column(TIMESTAMP)
    processing_completed_at = Column(TIMESTAMP)
    processing_error = Column(Text)
    meta_info = Column(JSON)  # بدل metadata
    project = relationship("Project", backref="vendor_documents")
    user = relationship("User", backref="vendor_documents")
    rfp = relationship("RFPDocument", backref="vendor_documents")

# ================= DOCUMENT CHUNKS ===================
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    document_type = Column(String(20), nullable=False)  # 'rfp' or 'vendor'
    chunk_index = Column(Integer, nullable=False)
    original_text = Column(Text, nullable=False)
    contextualized_text = Column(Text)
    token_count = Column(Integer)
    page_number = Column(Integer)
    headings = Column(JSON)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    orig_indices = Column(JSON)
    meta_info = Column(JSON)  # بدل metadata

# ================= RFP REQUIREMENTS ===================
class RFPRequirement(Base):
    __tablename__ = "rfp_requirements"
    requirement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfp_id = Column(UUID(as_uuid=True), ForeignKey("rfp_documents.rfp_id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id"))
    requirement_text = Column(Text, nullable=False)
    category = Column(String(100))
    priority = Column(String(20))
    weight = Column(DECIMAL(5,4))
    evaluation_labels = Column(JSON)
    extracted_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_mandatory = Column(Boolean, default=False)
    meta_info = Column(JSON)  # بدل metadata

# ================= VENDOR CAPABILITIES ===================
class VendorCapability(Base):
    __tablename__ = "vendor_capabilities"
    capability_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_doc_id = Column(UUID(as_uuid=True), ForeignKey("vendor_documents.vendor_doc_id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id"))
    capability_text = Column(Text, nullable=False)
    capability_type = Column(String(50))
    category = Column(String(100))
    evaluation_labels = Column(JSON)
    extracted_at = Column(TIMESTAMP, default=datetime.utcnow)
    meta_info = Column(JSON)  # بدل metadata

# ================= CHUNK ANALYSIS ===================
class ChunkAnalysis(Base):
    __tablename__ = "chunk_analysis"
    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(20), nullable=False)
    summary = Column(Text)
    requirements = Column(JSON)
    capabilities = Column(JSON)
    commitments = Column(JSON)
    differentiators = Column(JSON)
    evaluation_labels = Column(JSON)
    raw_model_output = Column(Text)
    analyzed_at = Column(TIMESTAMP, default=datetime.utcnow)
    model_used = Column(String(100))

# ================= EMBEDDINGS ===================
class Embedding(Base):
    __tablename__ = "embeddings"
    embedding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"))
    faiss_index_path = Column(Text, nullable=False)
    metadata_path = Column(Text, nullable=False)
    dimension = Column(Integer, nullable=False)
    total_vectors = Column(Integer, nullable=False)
    embedding_model = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class EmbeddingDocument(Base):
    __tablename__ = "embedding_documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    embedding_id = Column(UUID(as_uuid=True), ForeignKey("embeddings.embedding_id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    document_type = Column(String(20), nullable=False)
    included_at = Column(TIMESTAMP, default=datetime.utcnow)

# ================= CHATBOT ===================
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"))
    embedding_id = Column(UUID(as_uuid=True), ForeignKey("embeddings.embedding_id", ondelete="SET NULL"))
    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_interaction = Column(TIMESTAMP, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    sources = Column(JSON)
    tokens_used = Column(Integer)
    response_time_ms = Column(Integer)
    model_used = Column(String(100))

class QueryHistory(Base):
    __tablename__ = "query_history"
    query_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="SET NULL"))
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text)
    retrieved_chunks = Column(Integer)
    top_k = Column(Integer)
    execution_time_ms = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

# ================= EVALUATION ===================
class VendorEvaluation(Base):
    __tablename__ = "vendor_evaluations"
    evaluation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    vendor_doc_id = Column(UUID(as_uuid=True), ForeignKey("vendor_documents.vendor_doc_id", ondelete="CASCADE"), nullable=False)
    evaluator_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"))
    total_score = Column(DECIMAL(5,2))
    compliance_score = Column(DECIMAL(5,2))
    technical_score = Column(DECIMAL(5,2))
    financial_score = Column(DECIMAL(5,2))
    requirements_met = Column(Integer)
    total_requirements = Column(Integer)
    evaluation_notes = Column(Text)
    evaluation_data = Column(JSON)
    evaluated_at = Column(TIMESTAMP, default=datetime.utcnow)

class RequirementMatch(Base):
    __tablename__ = "requirement_matches"
    match_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("rfp_requirements.requirement_id", ondelete="CASCADE"), nullable=False)
    capability_id = Column(UUID(as_uuid=True), ForeignKey("vendor_capabilities.capability_id", ondelete="CASCADE"), nullable=False)
    match_score = Column(DECIMAL(5,4))
    match_type = Column(String(50))
    notes = Column(Text)
    matched_at = Column(TIMESTAMP, default=datetime.utcnow)
    matched_by = Column(String(50))

# ================= SYSTEM CONFIG & LOGS ===================
class SystemConfig(Base):
    __tablename__ = "system_config"
    config_key = Column(String(100), primary_key=True)
    config_value = Column(Text)
    description = Column(Text)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"))
    document_id = Column(UUID(as_uuid=True))
    document_type = Column(String(20))
    operation = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    error_message = Column(Text)
    duration_ms = Column(Integer)
    meta_info = Column(JSON)  # بدل metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
