For this project, first check the API reference file in the folder. We will be building a UI for this API. We just need a simple chatbot that accepts a user query, calls the API and then for a start let it return the JSON response of the LLM. 
THe chatbot does not have to accept any additional input like images or voice, just user text. We first have to plan what framework to build this in. The only UI framework I was familiar with was Streamlit but I don't know if streamlit is the best UI framework here. Do you think there are alternative UI frameworks we could use? 

The chatbot UI should also have some simple conversation saving ability -- but it can be ephermeral. It does not have to be saved after the session is closed. But within a session, the user should be able to start a new chat and go back to a previous chat. Also since the API does something very specific, we actually have to brainstorm is a "chat" is actually the right interface here as back and forth will be limited with this API. Maybe it makes more sense for the UI to start the conversation here? Like "What would you like to ask about SAP AI?" 

Instead of allowing the user to decide to go for an open ended question. Thoughts? Is it common for a gen ai application to be so specific like this as an API with limited functionality and if so does it make sense to be exposed through a chatbot interface? 

In the end the purpose of this UI is for people to try out the API and to show people what I have made with the API. Any feedback or thoughts are welcome and ask me any clarifying questions. 
