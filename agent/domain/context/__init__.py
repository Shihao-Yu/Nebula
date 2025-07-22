 # This module handles Context engineering
 
#  +---------------------+
# |      Memory         |   (Persistent, large, external)
# |---------------------|
# | Conversation logs   |
# | User embeddings     |
# | Tool results        |
# +---------------------+

# +---------------------+
# |      State          |   (Current, serialized, workflow-focused)
# |---------------------|
# | Step number         |
# | Active task         |
# | Current variables   |
# | Tool references     |
# +---------------------+

#    \    /
#     \  /
#      \/
# +------------------------------+
# |           Context            |   (Dynamically assembled for action)
# |------------------------------|
# | Current state (step, vars)   |
# | Relevant memory (N turns,    |
# |   embeddings, facts, etc)    |
# | Current input (msg/event)    |
# | Env info (time, etc)         |
# +------------------------------+
#         |
#         v
#   [LLM / policy / tool call]