"""
Chatbot logic for MRIG.

Uses a FAISS vector store built from llm_dataset.csv (a Q&A knowledge base
about the conditions detected by the CNN) to answer patient questions via
Retrieval-Augmented Generation (RAG).

NOTE: Google's PaLM API (langchain.llms.GooglePalm) has been shut down.
This module now uses Gemini (langchain-google-genai) instead.

Requires a GOOGLE_API_KEY environment variable (get one at
https://aistudio.google.com/app/apikey). Never hardcode API keys in source.
"""

import os

from dotenv import load_dotenv
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.embeddings import HuggingFaceInstructEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Load variables from a local .env file (see .env.example)
load_dotenv()

vectordb_file_path = "faiss_index"

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. Create a .env file (see .env.example) "
        "or export the variable before running the app."
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.001,
)

instructor_embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-large")


def create_vector_db():
    """Build the FAISS vector store from llm_dataset.csv and persist it to disk."""
    loader = CSVLoader(file_path="llm_dataset.csv", source_column="prompt")
    data = loader.load()

    vectordb = FAISS.from_documents(documents=data, embedding=instructor_embeddings)
    vectordb.save_local(vectordb_file_path)
    return vectordb


def load_vector_db():
    """Load a previously-persisted FAISS vector store from disk."""
    # allow_dangerous_deserialization is required by recent langchain versions
    # since loading a pickle can execute arbitrary code. This is safe here
    # because the index is one we generated ourselves from llm_dataset.csv,
    # not one accepted from an untrusted source.
    return FAISS.load_local(
        vectordb_file_path,
        instructor_embeddings,
        allow_dangerous_deserialization=True,
    )


def get_qa_chain(vectordb):
    """Build a RetrievalQA chain over the given vector store."""
    retriever = vectordb.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"score_threshold": 0.7},
    )

    prompt_template = """Given the following context and a question, generate an answer based on this context only.
    In the answer try to provide as much text as possible from the "response" section in the source document context without making much changes.
    If the answer is not found in the context, kindly state "I don't know." Don't try to make up an answer.

    CONTEXT: {context}

    QUESTION: {question}"""

    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        input_key="query",
        return_source_documents=False,
        chain_type_kwargs={"prompt": PROMPT},
    )

    return chain


def ask_question(chain_instance, query):
    response = chain_instance.invoke({"query": query})
    return response["result"]


if __name__ == "__main__":
    if not os.path.exists(vectordb_file_path):
        create_vector_db()

    vectordb = load_vector_db()
    chain_instance = get_qa_chain(vectordb)

    print(ask_question(chain_instance, "what's edema"))
