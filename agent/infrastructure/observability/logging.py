import structlog
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    service_name: str = "agent-server"
) -> None:
    """Setup structured logging configuration"""
    
    # Configure Python logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO)
    )
    
    # Processors for structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_service_context,
    ]
    
    # Add appropriate renderer based on format
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set service name in context
    structlog.contextvars.bind_contextvars(
        service=service_name,
        environment=os.getenv("ENVIRONMENT", "development"),
        version=os.getenv("SERVICE_VERSION", "unknown")
    )


def add_service_context(logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add service context to all log entries"""
    
    # Add timestamp if not present
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.utcnow().isoformat()
    
    # Add trace ID if available (from context)
    trace_id = structlog.contextvars.get_contextvars().get("trace_id")
    if trace_id:
        event_dict["trace_id"] = trace_id
    
    # Add session ID if available
    session_id = structlog.contextvars.get_contextvars().get("session_id")
    if session_id:
        event_dict["session_id"] = session_id
    
    return event_dict


class AgentLogger:
    """Specialized logger for agent operations"""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        
    def log_agent_event(
        self,
        event_type: str,
        agent_name: str,
        session_id: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log agent-specific events"""
        
        self.logger.info(
            "agent_event",
            event_type=event_type,
            agent_name=agent_name,
            session_id=session_id,
            data=data or {},
            **kwargs
        )
        
    def log_tool_execution(
        self,
        tool_name: str,
        session_id: str,
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log tool execution events"""
        
        self.logger.info(
            "tool_execution",
            tool_name=tool_name,
            session_id=session_id,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            success=success,
            error=error
        )
        
    def log_workflow_transition(
        self,
        session_id: str,
        from_node: str,
        to_node: str,
        condition: Optional[str] = None,
        state_summary: Optional[Dict[str, Any]] = None
    ):
        """Log workflow state transitions"""
        
        self.logger.info(
            "workflow_transition",
            session_id=session_id,
            from_node=from_node,
            to_node=to_node,
            condition=condition,
            state_summary=state_summary or {}
        )
        
    def log_context_update(
        self,
        session_id: str,
        context_type: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log context updates"""
        
        self.logger.info(
            "context_update",
            session_id=session_id,
            context_type=context_type,
            action=action,
            details=details or {}
        )


# Global logger instance
agent_logger = AgentLogger("agent")


class MetricsCollector:
    """Collect and export metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {}
        
    def record_latency(self, operation: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Record operation latency"""
        
        key = f"latency.{operation}"
        if key not in self.metrics:
            self.metrics[key] = {
                "count": 0,
                "sum": 0,
                "min": float('inf'),
                "max": 0
            }
            
        self.metrics[key]["count"] += 1
        self.metrics[key]["sum"] += duration_ms
        self.metrics[key]["min"] = min(self.metrics[key]["min"], duration_ms)
        self.metrics[key]["max"] = max(self.metrics[key]["max"], duration_ms)
        
        # Log metric
        agent_logger.logger.info(
            "metric",
            metric_type="latency",
            operation=operation,
            duration_ms=duration_ms,
            tags=tags or {}
        )
        
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        
        if name not in self.metrics:
            self.metrics[name] = 0
        self.metrics[name] += value
        
        # Log metric
        agent_logger.logger.info(
            "metric",
            metric_type="counter",
            name=name,
            value=value,
            tags=tags or {}
        )
        
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        
        self.metrics[name] = value
        
        # Log metric
        agent_logger.logger.info(
            "metric",
            metric_type="gauge",
            name=name,
            value=value,
            tags=tags or {}
        )
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        
        summary = {}
        for key, value in self.metrics.items():
            if isinstance(value, dict) and "count" in value:
                # Latency metric
                summary[key] = {
                    "count": value["count"],
                    "avg": value["sum"] / value["count"] if value["count"] > 0 else 0,
                    "min": value["min"] if value["min"] != float('inf') else 0,
                    "max": value["max"]
                }
            else:
                # Counter or gauge
                summary[key] = value
                
        return summary


# Global metrics collector
metrics = MetricsCollector()