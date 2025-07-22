 # Langfuse integration
 from langfuse import Langfuse
from langfuse.decorators import observe

class EnterpriseObservabilityManager:
    def __init__(self, langfuse_config, clickhouse_config):
        self.langfuse = Langfuse(
            public_key=langfuse_config.public_key,
            secret_key=langfuse_config.secret_key,
            host=langfuse_config.host
        )
        self.clickhouse = ClickHouseLogger(clickhouse_config)
        self.metrics_collector = MetricsCollector()
    
    @observe(name="agent_workflow_execution")
    async def trace_agent_workflow(self, workflow_id: str, user_id: str, tenant_id: str):
        # Set trace metadata
        self.langfuse.update_current_trace(
            user_id=user_id,
            session_id=f"agent_{user_id}_{workflow_id}",
            tags=["production", "workflow", tenant_id],
            metadata={
                "tenant_id": tenant_id,
                "workflow_type": "multi_agent",
                "execution_environment": "production"
            }
        )
    
    @observe(name="tool_execution")
    async def trace_tool_execution(self, tool_name: str, parameters: Dict[str, Any], execution_result: ToolResult):
        # Custom metrics for tool performance
        self.langfuse.update_current_observation(
            input=parameters,
            output=execution_result.data if execution_result.success else execution_result.error,
            metadata={
                "tool_name": tool_name,
                "execution_time": execution_result.execution_time,
                "success": execution_result.success,
                "resource_usage": execution_result.resource_usage
            }
        )
        
        # Real-time metrics to ClickHouse
        await self.clickhouse.log_tool_execution(
            tool_name=tool_name,
            execution_time=execution_result.execution_time,
            success=execution_result.success,
            timestamp=time.time()
        )