import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List

from google.genai import Client, types

from app.core.config import settings
from app.schemas.rules import RuleListItemSchema

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def generate_spanish_explanation(
    client: Client,
    query: str,
    context: str,
    user_level: str,
    lang: str
) -> str:
    """Generates a grammar explanation from Gemini based on RAG context."""
    system_instruction = (
        f"You are an expert Spanish teacher. "
        f"The student's current proficiency level is {user_level}. "
        f"You will be provided with grammar rules that have their own difficulty 'level' markers. "
        f"TASK: Explain the grammar using the provided context. "
        f"If the rule's level is HIGHER than the student's level, simplify your explanation significantly. "
        f"If the rule's level matches the student's level, provide a detailed pedagogical breakdown. "
        f"Always respond strictly in the {lang} language."
    )

    prompt = (
        f"Based on the provided grammar rules:\n"
        f"--- CONTEXT START ---\n"
        f"{context}\n"
        f"--- CONTEXT END ---\n\n"
        f"Answer the user's question: '{query}'.\n"
        f"Requirements:\n"
        f"1. Give a brief but clear explanation.\n"
        f"2. Provide 3 practical examples in Spanish with translations.\n"
        f"3. Use only the provided context if possible."
    )

    try:
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
            )
        )

        if not response.text:
            return "Sorry, could not generate an explanation."

        return response.text

    except Exception as e:
        logging.error(f"Error calling Gemini API for explanation generation: {e}")
        raise e


async def verify_user_answer(
    client: Client,
    rule_context: str,
    user_answer: str,
    exercise_type: str,
    original_question: str,
    correct_answer_example: str,
    lang: str
) -> Dict[str, Any]:
    """Evaluates a user's answer to an exercise."""
    system_instruction = (
        f"You are a strict but encouraging Spanish teacher. "
        f"Your task is to evaluate the user's answer to a specific grammar exercise. "
        f"Provide a score from 0-10, a correct version of the answer, and a short explanation. "
        f"Respond in {lang}."
    )

    prompt = f"""
        Context of the grammar rule (for background reference only):
        --- RULE CONTEXT START ---
        {rule_context}
        --- RULE CONTEXT END ---

        Specific Exercise Details:
        - Exercise Type: {exercise_type}
        - Original Question/Prompt: {original_question}
        - Expected Correct Answer/Example: {correct_answer_example}

        User's Answer: "{user_answer}"

        Task: Evaluate the user's answer based PRIMARILY on the 'Specific Exercise Details' and SECONDARILY on the 'Context of the grammar rule'.
        Return ONLY a JSON object:
        {{
            "score": (0-10, where 10 is perfect),
            "correct_version": "The correct version of the user's answer in Spanish, or the correct answer if it was a fill-in-the-blank/multiple-choice. If the user's answer is perfect, repeat it.",
            "explanation": "A short, constructive explanation in {lang} about why the answer received its score, referencing the specific exercise and the grammar rule if applicable."
        }}
        """

    try:
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL_NAME,
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "temperature": 0.3,
            }
        )

        raw_text = response.text
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            clean_json = re.sub(r'```json|```', '', raw_text).strip()
            try:
                return json.loads(clean_json)
            except Exception:
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise Exception("Could not parse Gemini response as JSON")

    except Exception as e:
        logging.error(f"Error calling Gemini API for answer verification: {e}")
        raise e


async def generate_explanation(
    client: Client,
    context_text: str,
    target_level: str,
    lang: str,
    rule_id: str
) -> str:
    """Generates a rule explanation adapted to a specific target level."""
    system_instruction = (
        f"You are an expert Spanish teacher. "
        f"Your task is to generate a clear, concise, and pedagogically sound explanation "
        f"of a Spanish grammar rule for a student at the {target_level} proficiency level. "
        f"The explanation must be based STRICTLY on the provided context. "
        f"Adapt the complexity and vocabulary of your explanation to the {target_level}. "
        f"Always respond strictly in the {lang} language."
    )

    prompt = (
        f"Based on the following grammar rule context:\n"
        f"--- CONTEXT START ---\n"
        f"{context_text}\n"
        f"--- CONTEXT END ---\n\n"
        f"Please provide an explanation for the rule identified as '{rule_id}'.\n"
        f"Requirements:\n"
        f"1. The explanation should be suitable for a student at the {target_level} level.\n"
        f"2. Include 2-3 practical examples in Spanish with their {lang} translations.\n"
        f"3. Do not introduce information not present in the context.\n"
        f"4. Structure your explanation clearly with headings or bullet points if appropriate.\n"
        f"5. IMPORTANT: If the context contains a Markdown table that is relevant to the explanation, reproduce it accurately in your response. Do not convert tables to prose."
    )

    try:
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.5,
            )
        )

        if not response.text:
            return "Sorry, could not generate an explanation."

        return response.text

    except Exception as e:
        logging.error(f"Error calling Gemini API for explanation generation: {e}")
        raise e


async def generate_exercises(
    client: Client,
    rule_context: str,
    target_level: str,
    lang: str,
    rule_id: str
) -> List[Dict[str, Any]]:
    """Generates exercises for a rule based on context and target level."""
    system_instruction = (
        f"You are an expert Spanish teacher. "
        f"Your task is to generate diverse grammar exercises for a student at the {target_level} proficiency level. "
        f"The exercises must be based STRICTLY on the provided rule context. "
        f"Ensure the difficulty is appropriate for {target_level}. "
        f"Always provide responses in {lang} for instructions and translations."
    )

    prompt = f"""
        Based on the following Spanish grammar rule context (Rule ID: {rule_id}):
        --- CONTEXT START ---
        {rule_context}
        --- CONTEXT END ---

        Generate a list of 9 exercises for a student at the {target_level} level.
        The exercises should be structured as follows:
        - 3 exercises of type "fill_in_the_blank"
        - 3 exercises of type "multiple_choice"
        - 3 exercises of type "free_response"

        Return ONLY a JSON array of objects. Each object in the array must have the following structure based on its type:

        **For Fill-in-the-blank:**
        {{
            "type": "fill_in_the_blank",
            "question": "El ___ es rojo.",
            "correct_answer": "coche",
            "translation": "The car is red."
        }}

        **For Multiple Choice:**
        {{
            "type": "multiple_choice",
            "question": "¿Cuál es la forma correcta del verbo 'ser' для 'yo'?",
            "options": ["soy", "eres", "es"],
            "correct_answer": "soy",
            "translation": "What is the correct form of the verb 'to be' for 'I'?"
        }}

        **For Free Response:**
        {{
            "type": "free_response",
            "question": "Traduce la siguiente frase al español: 'I eat apples'.",
            "correct_answer": "Yo como manzanas",
            "translation": "Translate the following sentence into Spanish: 'I eat apples'."
        }}

        Ensure all Spanish sentences and options are grammatically correct according to the rule.
        The 'translation' field should be in {lang}.
        """

    try:
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL_NAME,
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "temperature": 0.7,
            }
        )

        raw_text = response.text
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            clean_json = re.sub(r'```json|```', '', raw_text).strip()
            try:
                return json.loads(clean_json)
            except Exception:
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise Exception(f"Could not parse Gemini exercises response as JSON: {raw_text}")

    except Exception as e:
        logging.error(f"Error calling Gemini API for exercise generation: {e}")
        raise e


async def generate_chatbot_answer(
    client: Client,
    query: str,
    context: str,
    user_level: str,
    lang: str,
    source_rules: List[RuleListItemSchema]
) -> AsyncGenerator[Dict[str, Any], None]:
    """Generates streaming chatbot answers using RAG context."""
    system_instruction = (
        f"You are a helpful and knowledgeable Spanish grammar assistant. "
        f"Your goal is to answer the user's question clearly and concisely, "
        f"using ONLY the provided context. "
        f"If the context is insufficient, state that you cannot answer based on the provided information. "
        f"Adapt your language to a student at the {user_level} proficiency level. "
        f"Always respond strictly in {lang}."
    )

    available_rules_list = ""
    if source_rules:
        available_rules_list = "\n\n--- Available Rules for Reference ---\n"
        for rule_info in source_rules:
            available_rules_list += f"- {rule_info.display_title or rule_info.chunk_id}\n"

    prompt = (
        f"Based on the following grammar rule context:\n"
        f"--- CONTEXT START ---\n"
        f"{context}\n"
        f"--- CONTEXT END ---\n\n"
        f"Answer the user's question: '{query}'.\n"
        f"Requirements:\n"
        f"1. Provide a direct and helpful answer.\n"
        f"2. Do not introduce information not present in the context.\n"
        f"3. If you use information from the context, integrate it naturally into your answer.\n"
        f"4. At the end of your answer, provide a JSON object with two keys: 'answer_text' (your main answer) and 'relevant_rule_titles' (a list of titles of rules from the 'Available Rules for Reference' section that were directly used to formulate your answer. These titles must EXACTLY match the titles provided in the 'Available Rules for Reference' section).\n"
        f"Return ONLY this JSON object.\n"
        f"{available_rules_list}"
    )

    try:
        response_stream = await client.aio.models.generate_content_stream(
            model=settings.GEMINI_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
            ),
        )

        full_llm_raw_output = ""
        async for chunk in response_stream:
            if chunk.text:
                full_llm_raw_output += chunk.text

        try:
            json_match = re.search(r'\{.*\}', full_llm_raw_output, re.DOTALL)
            if not json_match:
                raise json.JSONDecodeError("No JSON object found in LLM response", full_llm_raw_output, 0)

            llm_response_dict = json.loads(json_match.group(0))
            answer_text = llm_response_dict.get("answer_text", "Sorry, could not generate an answer.")
            relevant_rule_titles = llm_response_dict.get("relevant_rule_titles", [])

            for char in answer_text:
                yield {"type": "text", "content": char}
                await asyncio.sleep(0.005)

            yield {"type": "final", "relevant_rule_titles": relevant_rule_titles}

        except json.JSONDecodeError as e:
            logging.error(f"GENERATE_CHATBOT_ANSWER: Could not parse final LLM response as JSON: {e}")
            yield {"type": "error", "content": f"Could not parse final LLM response as JSON: {e}"}

    except Exception as e:
        logging.error(f"Error calling Gemini API for chatbot answer generation: {e}")
        yield {"type": "error", "content": f"Chatbot LLM Service Error: {str(e)}"}


async def generate_additional_exercises(
    client: Client,
    rule_context: str,
    target_level: str,
    lang: str,
    exercise_type: str
) -> List[Dict[str, Any]]:
    """Generates additional exercises of a specific type based on rule context."""
    system_instruction = (
        f"You are an expert Spanish teacher. "
        f"Your task is to generate 5 additional grammar exercises of type '{exercise_type}' "
        f"for a student at the {target_level} proficiency level. "
        f"The exercises must be based STRICTLY on the provided rule context. "
        f"Ensure the difficulty is appropriate for {target_level}. "
        f"Always provide responses in {lang} for instructions and translations."
    )

    exercise_format_instruction = ""
    if exercise_type == "fill_in_the_blank":
        exercise_format_instruction = """
        **For Fill-in-the-blank:**
        {
            "type": "fill_in_the_blank",
            "question": "El ___ es rojo.",
            "correct_answer": "coche",
            "translation": "The car is red."
        }
        """
    elif exercise_type == "multiple_choice":
        exercise_format_instruction = """
        **For Multiple Choice:**
        {
            "type": "multiple_choice",
            "question": "¿Cuál es la forma correcta del verbo 'ser' para 'yo'?",
            "options": ["soy", "eres", "es"],
            "correct_answer": "soy",
            "translation": "What is the correct form of the verb 'to be' for 'I'?"
        }
        """
    elif exercise_type == "free_response":
        exercise_format_instruction = """
        **For Free Response:**
        {
            "type": "free_response",
            "question": "Traduce la siguiente frase al español: 'I eat apples'.",
            "correct_answer": "Yo como manzanas",
            "translation": "Translate the following sentence into Spanish: 'I eat apples'."
        }
        """
    else:
        raise ValueError(f"Unsupported exercise type: {exercise_type}")

    prompt = f"""
        Based on the following Spanish grammar rule context:
        --- CONTEXT START ---
        {rule_context}
        --- CONTEXT END ---

        Generate a list of 5 exercises of type '{exercise_type}' for a student at the {target_level} level.
        Return ONLY a JSON array of objects. Each object in the array must have the following structure:
        {exercise_format_instruction}

        Ensure all Spanish sentences and options are grammatically correct according to the rule.
        The 'translation' field should be in {lang}.
        """

    try:
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL_NAME,
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "temperature": 0.7,
            }
        )

        raw_text = response.text
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            clean_json = re.sub(r'```json|```', '', raw_text).strip()
            try:
                return json.loads(clean_json)
            except Exception:
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise Exception(f"Could not parse Gemini exercises response as JSON: {raw_text}")

    except Exception as e:
        logging.error(f"Error calling Gemini API for additional exercise generation: {e}")
        raise e
