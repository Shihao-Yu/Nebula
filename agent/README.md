1.1 This repo serves as a complex agentic server that expose as an fast api or a websocket or a sdk, as the very step we should only implement websocket server, but we should leave the space for extensibility.

2.1 The application folder contains three major interface I discussed above

3.1 The domain folder is the core agent server component, we will use the latest, modern agentic architecture, consider use instructor as pydantic model schema

3.1.1 we should implement a scalable, generic multi-agent, we will a N0 - IAC architcture.
3.2.1 we need to implement powerful context engineering, context is a assembly of state, memory, and available subagent/tools/mcp context it has.
3.3.1 the way agent communicate with websocket should be event based with a pre-defined contract, this way we make sure that we provide responsive and smooth user experience, the agent should be able to give real-time event response what it's doing(of course we will have intermeridate steps that we don't wnat to expose)
3.3.2 we should be able to switch model for different use cases...

3.3.2 some user's request might be "what is ...."， "search xxx",
3.3.3 some user's request might be "They dragged an file and say create a purchase order with this, we should be able to invoke pdf parser, resolve fileds into a purchase order fields, call a few APIs to resolve the data, and might require human-in-the-loop to review the data..."
3.3.4 if user interrupt, agent should be to restore the state and carry on as intended

4.1 a few examples here how the contract is defined with UI component:

5.1 initially, for any IO, like API request, or db all or pdf, you don't need to really implement them, we should start with core stone of our agent which is the orchestration, you can have some mock response for these.
Contract:

Normal message: this is a chunked markdown supported data, which is the main chat message that we would like to show to user

     {
       "type": "markdown",
       "payload": "## Hello! Here's some **bold** text.\n\n- List item 1\n- List item 2"
     }

Progress: this is the internal progress of what currently the agent is working on

     {
       "type": "component",
       "payload": {
         "component": "progress",
         "data": {
           "status": "Analyzing your request..."
         }
       }
     }



Step: this will show like a sequential list what the agent is going to do
     {
       "type": "component",
       "payload": {
         "component": "progress",
         "data": {
           "status": "Step 2: Fetching data",
           "stepIndex": 2,
           "totalSteps": 5
         }
       }
     }


Workflow Finish: this is soemthing we are notifying the UI component and user's request has been fulfilled
     {
       "type": "component",
       "payload": {
         "component": "progress",
         "data": {
           "status": "_workflow_finish"
         }
       }
     }


UI-form, this means UI is submitting a form response back to agent server

     {
       "type": "component",
       "payload": {
         "component": "ui_interaction",
         "data": {
           "form": {
             "id": "form-123",
             "title": "Please provide details",
             "fields": [
               {
                 "type": "text",
                 "key": "name",
                 "label": "Your Name",
                 "required": true,
                 "placeholder": "Enter your full name",
                 "validation": [{"type": "required", "message": "Name is required"}]
               },
               {
                 "type": "select",
                 "key": "color",
                 "label": "Favorite Color",
                 "options": [
                   {"value": "red", "label": "Red"},
                   {"value": "blue", "label": "Blue"}
                 ],
                 "async": false,
                 "placeholder": "Select a color"
               }
             ]
           }
         }
       }
     }


Async select, this means ui want to query more data for a field
     {
       "type": "component",
       "payload": {
         "component": "ui_interaction",
         "data": {
           "form": {
             "id": "search-form-456",
             "fields": [
               {
                 "type": "select",
                 "key": "supplier",
                 "label": "Supplier",
                 "async": true,
                 "searchable": true,
                 "dataSource": {
                   "provider": "supplier_search",
                   "minChars": 3,
                   "debounceMs": 500,
                   "pageSize": 20
                 },
                 "options": [], // Initial empty; populated by backend responses
                 "placeholder": "Search suppliers..."
               }
             ]
           }
         }
       }
     }
