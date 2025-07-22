# Parameter & Security Validation
class ToolParameterValidator:
    @staticmethod
    def validate_tool_call(tool: ToolInterface, parameters: Dict[str, Any]) -> ValidationResult:
        schema = tool.parameters_schema
        
        try:
            # JSON Schema validation
            jsonschema.validate(parameters, schema)
            
            # Custom business logic validation
            if hasattr(tool, 'custom_validation'):
                custom_result = tool.custom_validation(parameters)
                if not custom_result.is_valid:
                    return ValidationResult(False, custom_result.errors)
            
            # Security validation
            security_issues = SecurityValidator.check_parameters(parameters, tool.required_permissions)
            if security_issues:
                return ValidationResult(False, security_issues)
                
            return ValidationResult(True, [])
            
        except jsonschema.ValidationError as e:
            return ValidationResult(False, [f"Schema validation failed: {e.message}"])