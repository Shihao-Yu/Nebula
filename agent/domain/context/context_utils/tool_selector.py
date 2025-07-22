# # context/tool_selector.py

# class ToolSelector:
#     def __init__(self, tools_registry):
#         self.tools_registry = tools_registry

#     def select_tool(self, context):
#         # Example: LLM-driven selection (simplified)
#         if context['tools']:
#             llm_output = call_llm_with_tools(context)
#             if llm_output['tool']:
#                 tool_name = llm_output['tool']
#                 tool_args = llm_output['args']
#                 return self.tools_registry.get_tool(tool_name), tool_args
#         return None, None
