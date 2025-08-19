"""
Data models for the feedback and classification system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid
import re


@dataclass
class Analysis:
    """
    Data model for log analysis results.
    Represents a complete analysis with all required fields for database storage.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    erro: str = ""
    causa: str = ""
    solucao: str = ""
    criticidade: str = ""
    origem: str = ""
    log_original: str = ""
    solucao_valida: Optional[str] = None
    solucao_editada: Optional[str] = None
    timestamp_analise: datetime = field(default_factory=datetime.now)
    data_incidente: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate data after initialization."""
        self.validate()

    def validate(self):
        """
        Validate analysis data according to requirements.
        Raises ValueError if validation fails.
        """
        if not self.erro.strip():
            raise ValueError("Campo 'erro' é obrigatório")
        
        if not self.causa.strip():
            raise ValueError("Campo 'causa' é obrigatório")
        
        if not self.solucao.strip():
            raise ValueError("Campo 'solucao' é obrigatório")
        
        valid_criticidades = ["baixa", "media", "alta"]
        if self.criticidade.lower() not in valid_criticidades:
            raise ValueError(f"Criticidade deve ser uma das opções: {valid_criticidades}")
        
        if not self.log_original.strip():
            raise ValueError("Campo 'log_original' é obrigatório")
        
        if self.solucao_valida is not None and self.solucao_valida not in ["true", "false"]:
            raise ValueError("Campo 'solucao_valida' deve ser 'true', 'false' ou None")

    def to_dict(self):
        """
        Convert Analysis to dictionary format.
        Returns dictionary with all fields.
        """
        return {
            "id": self.id,
            "erro": self.erro,
            "causa": self.causa,
            "solucao": self.solucao,
            "criticidade": self.criticidade,
            "origem": self.origem,
            "log_original": self.log_original,
            "solucao_valida": self.solucao_valida,
            "solucao_editada": self.solucao_editada,
            "timestamp_analise": self.timestamp_analise.isoformat(),
            "data_incidente": self.data_incidente
        }


@dataclass
class Classification:
    """
    Data model for solution classification and feedback.
    Used when users provide feedback on AI-generated solutions.
    """
    analysis_id: str
    solucao_valida: bool
    solucao_editada: Optional[str] = None
    timestamp_classificacao: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate data after initialization."""
        self.validate()

    def validate(self):
        """
        Validate classification data.
        Raises ValueError if validation fails.
        """
        if not self.analysis_id.strip():
            raise ValueError("Campo 'analysis_id' é obrigatório")
        
        # Validate UUID format
        try:
            uuid.UUID(self.analysis_id)
        except ValueError:
            raise ValueError("Campo 'analysis_id' deve ser um UUID válido")
        
        if not isinstance(self.solucao_valida, bool):
            raise ValueError("Campo 'solucao_valida' deve ser boolean")
        
        if self.solucao_editada is not None and not self.solucao_editada.strip():
            raise ValueError("Campo 'solucao_editada' não pode ser string vazia")

    def to_update_fields(self):
        """
        Convert Classification to fields for database update.
        Returns dictionary with fields to update.
        """
        return {
            "solucao_valida": "true" if self.solucao_valida else "false",
            "solucao_editada": self.solucao_editada
        }


def parse_ai_response(ai_response: str) -> dict:
    """
    Parse AI response text to extract structured data.
    
    Args:
        ai_response: Raw response text from AI
        
    Returns:
        Dictionary with parsed fields: erro, causa, solucao, criticidade
    """
    if not ai_response or not ai_response.strip():
        raise ValueError("Resposta da IA não pode estar vazia")
    
    # Extract information using regex patterns
    erro_match = re.search(r"1\.\s*(.+?)(?:\n|$)", ai_response, re.MULTILINE)
    causa_match = re.search(r"2\.\s*(.+?)(?:\n|$)", ai_response, re.MULTILINE)
    solucao_match = re.search(r"3\.\s*(.+?)(?:\n|$)", ai_response, re.MULTILINE)
    criticidade_match = re.search(r"4\.\s*(.+?)(?:\n|$)", ai_response, re.MULTILINE)
    
    erro = erro_match.group(1).strip() if erro_match else "Não identificado"
    causa = causa_match.group(1).strip() if causa_match else "Não identificado"
    solucao = solucao_match.group(1).strip() if solucao_match else "Não identificado"
    criticidade = criticidade_match.group(1).strip().lower() if criticidade_match else "baixa"
    
    # Normalize criticidade
    if "alta" in criticidade:
        criticidade = "alta"
    elif "media" in criticidade or "média" in criticidade:
        criticidade = "media"
    else:
        criticidade = "baixa"
    
    return {
        "erro": erro,
        "causa": causa,
        "solucao": solucao,
        "criticidade": criticidade
    }