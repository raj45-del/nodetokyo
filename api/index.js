const { GoogleGenerativeAI } = require('@google/generative-ai');

// Gemini model to use
const MODEL_NAME = 'gemini-3.1-flash-lite';


// Mode-specific system prompts
const SYSTEM_PROMPTS = {
    dsa: `You are a competitive programming and DSA expert.
Solve the given problem directly. Give only the code or the direct answer.
If it is a multiple choice question, give only the correct option (A/B/C/D or 1/2/3/4).
No explanations. No preamble. Just the answer.`,

    aptitude: `You are an aptitude and logical reasoning expert.
Solve the given question and give only the answer option (A/B/C/D or 1/2/3/4).
Do not explain. Just the answer.`,

    fullstack: `You are a full-stack web development expert.
Answer the question concisely. If MCQ, give only the option letter.
If it needs code, give clean minimal code only. No extra text.`,

    aws: `You are an AWS cloud computing expert.
Answer the question concisely. If MCQ, give only the option letter.
No explanation. Just the answer.`,

    ocr: `You are a precise OCR (Optical Character Recognition) tool.
Extract and return all the text visible in the image verbatim.
Maintain the original formatting, line breaks, and structure of the text as closely as possible.
Do not explain, summarize, or translate the text. Do not add any introduction, commentary, or notes.
Output ONLY the raw extracted text.`,

    copypaste: `You are a precise OCR (Optical Character Recognition) tool.
Extract and return all the text visible in the image verbatim.
Maintain the original formatting, line breaks, and structure of the text as closely as possible.
Do not explain, summarize, or translate the text. Do not add any introduction, commentary, or notes.
Output ONLY the raw extracted text.`,
};

module.exports = async (req, res) => {
    // CORS headers (allow all origins for local client use)
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    // Handle preflight
    if (req.method === 'OPTIONS') return res.status(200).end();
    if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
        return res.status(500).json({ error: 'GEMINI_API_KEY not set in environment variables.' });
    }

    try {
        const { text, image, mode } = req.body;

        // Pick prompt based on mode, default to dsa
        const systemPrompt = SYSTEM_PROMPTS[mode] || SYSTEM_PROMPTS.dsa;

        const genAI = new GoogleGenerativeAI(apiKey);
        const model = genAI.getGenerativeModel({ model: MODEL_NAME });

        let result;

        if (image) {
            
            const prompt = (mode === 'ocr' || mode === 'copypaste')
                ? systemPrompt
                : systemPrompt + '\n\nAnalyze the screenshot below and answer the question shown in it.';
            result = await model.generateContent([
                prompt,
                {
                    inlineData: {
                        mimeType: 'image/jpeg',
                        data: image,
                    },
                },
            ]);
        } else if (text && text.trim().length > 0) {
            // Text Mode: clipboard content
            result = await model.generateContent(`${systemPrompt}\n\nQuestion:\n${text}`);
        } else {
            return res.status(400).json({ error: 'No input provided. Send text or image.' });
        }

        const answer = result.response.text().trim();
        return res.status(200).json({ answer });

    } catch (err) {
        console.error('NodeTokyo API Error:', err.message);
        return res.status(500).json({ error: 'AI request failed.', details: err.message });
    }
};
