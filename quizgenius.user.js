// ==UserScript==
// @name         QuizGenius - Auto Solve McGraw Hill
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Automatically solves McGraw Hill quizzes using AI
// @author       QuizGenius
// @match        https://*.mheducation.com/*
// @match        https://*.connect.mheducation.com/*
// @match        https://learning.mheducation.com/*
// @icon         https://quizgenius.app/icon.png
// @grant        GM_xmlhttpRequest
// @grant        GM_notification
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      *
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    // API URL - update this after deploying to Render
    let API_BASE_URL = GM_getValue('apiUrl', '');
    let userId = null;
    let apiKey = null;
    let isRunning = false;
    let questionDelay = 5000;

    // UI Elements
    let controlPanel = null;

    function createControlPanel() {
        if (controlPanel) return;

        controlPanel = document.createElement('div');
        controlPanel.id = 'quizgenius-panel';
        controlPanel.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 99999;
                background: linear-gradient(135deg, #0a0a14 0%, #12121f 100%);
                border: 1px solid #1e1e2e;
                border-radius: 16px;
                padding: 20px;
                color: white;
                font-family: 'Outfit', sans-serif;
                min-width: 280px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            ">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
                    <div style="width:36px;height:36px;background:linear-gradient(135deg,#00d4aa,#00b894);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;">Q</div>
                    <span style="font-weight:700;font-size:18px;">QuizGenius</span>
                </div>

                <div id="qg-status" style="font-size:13px;color:#9ca3af;margin-bottom:16px;">
                    Ready to solve your quiz!
                </div>

                <div style="display:flex;flex-direction:column;gap:10px;">
                    <button id="qg-start" style="
                        padding: 12px;
                        background: linear-gradient(135deg,#00d4aa,#00b894);
                        border: none;
                        border-radius: 10px;
                        color: #000;
                        font-weight: 600;
                        cursor: pointer;
                    ">Start Solving</button>

                    <button id="qg-stop" style="
                        padding: 12px;
                        background: rgba(255,255,255,0.05);
                        border: 1px solid #1e1e2e;
                        border-radius: 10px;
                        color: #fff;
                        font-weight: 600;
                        cursor: pointer;
                        display: none;
                    ">Stop</button>

                        <div style="font-size:12px;color:#6b7280;">
                        <div>API Key (or leave blank if using account):</div>
                        <input id="qg-apikey" type="password" placeholder="gsk_..." style="
                            width:100%;padding:8px 12px;margin-top:4px;
                            background:rgba(255,255,255,0.05);
                            border:1px solid #1e1e2e;
                            border-radius:8px;color:#fff;font-size:12px;
                        ">
                        <div style="margin-top:8px;">User ID (optional):</div>
                        <input id="qg-userid" type="text" placeholder="Your account ID" style="
                            width:100%;padding:8px 12px;margin-top:4px;
                            background:rgba(255,255,255,0.05);
                            border:1px solid #1e1e2e;
                            border-radius:8px;color:#fff;font-size:12px;
                        ">
                        <div style="margin-top:8px;">API URL (optional):</div>
                        <input id="qg-apiurl" type="text" placeholder="https://your-app.onrender.com" style="
                            width:100%;padding:8px 12px;margin-top:4px;
                            background:rgba(255,255,255,0.05);
                            border:1px solid #1e1e2e;
                            border-radius:8px;color:#fff;font-size:12px;
                        ">
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(controlPanel);

        // Load saved values
        const savedKey = GM_getValue('apiKey', '');
        const savedUser = GM_getValue('userId', '');
        const savedUrl = GM_getValue('apiUrl', '');
        if (savedKey) document.getElementById('qg-apikey').value = savedKey;
        if (savedUser) document.getElementById('qg-userid').value = savedUser;
        if (savedUrl) document.getElementById('qg-apiurl').value = savedUrl;

        // Event listeners
        document.getElementById('qg-start').addEventListener('click', startSolving);
        document.getElementById('qg-stop').addEventListener('click', stopSolving);
    }

    function updateStatus(msg) {
        const el = document.getElementById('qg-status');
        if (el) el.textContent = msg;
    }

    function saveConfig() {
        apiKey = document.getElementById('qg-apikey').value.trim();
        userId = document.getElementById('qg-userid').value.trim();
        API_BASE_URL = document.getElementById('qg-apiurl').value.trim();
        GM_setValue('apiKey', apiKey);
        GM_setValue('userId', userId);
        GM_setValue('apiUrl', API_BASE_URL);
    }

    async function getAnswerFromAPI(question, options, type) {
        try {
            let finalKey = apiKey;
            let apiUrl = API_BASE_URL;

            // If user ID provided and API URL set, try to get key from API
            if (userId && apiUrl) {
                try {
                    const resp = await fetch(`${apiUrl}/api/sync`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: userId, action: 'get_key'})
                    });
                    const data = await resp.json();
                    if (data.api_key) finalKey = data.api_key;
                } catch(e) {
                    console.log('Could not fetch key from API, using direct key');
                }
            }

            if (!finalKey) {
                updateStatus('ERROR: No API key');
                return null;
            }

            // Use Groq API directly
            const resp = await fetch('https://api.groq.com/openai/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${finalKey}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: 'llama-3.1-8b-instant',
                    messages: [{
                        role: 'user',
                        content: `Question: ${question}\nType: ${type}\nOptions: ${options.join('\n')}\n\nWhat is the correct answer? Just respond with the option text.`
                    }],
                    temperature: 0.1
                })
            });

            const data = await resp.json();
            return data.choices[0].message.content.trim();
        } catch (e) {
            console.error('API Error:', e);
            return null;
        }
    }

    function parseQuestion() {
        // Try to find question text
        let questionText = '';

        // Common selectors for McGraw Hill
        const selectors = [
            '[data-automation-id="question-text"]',
            '.question-text',
            '.question-body',
            '[class*="question"]',
            'h1', 'h2', 'h3'
        ];

        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.textContent.trim().length > 10) {
                questionText = el.textContent.trim();
                break;
            }
        }

        // Find options
        const options = [];
        const optionSelectors = [
            '[data-automation-id*="option"]',
            '.option-text',
            '.answer-option',
            'label',
            '[class*="option"]'
        ];

        for (const sel of optionSelectors) {
            const els = document.querySelectorAll(sel);
            els.forEach(el => {
                const text = el.textContent.trim();
                if (text.length > 2 && text.length < 200) {
                    options.push(text);
                }
            });
        }

        // Get question type
        let questionType = 'Multiple Choice';
        const typeEl = document.querySelector('[data-automation-id*="type"], .question-type, [class*="type"]');
        if (typeEl) questionType = typeEl.textContent.trim();

        return { questionText, options, questionType };
    }

    function findOptionElement(answerText) {
        if (!answerText) return null;

        // Try exact match first
        const allElements = document.querySelectorAll('button, label, div[role="radio"], div[class*="option"]');

        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text.includes(answerText) || answerText.includes(text)) {
                return el;
            }
        }

        return null;
    }

    async function solveNextQuestion() {
        if (!isRunning) return;

        const question = parseQuestion();

        if (!question.questionText || question.questionText.length < 5) {
            updateStatus('No question found, waiting...');
            setTimeout(solveNextQuestion, 2000);
            return;
        }

        updateStatus(`Solving: ${question.questionText.substring(0, 50)}...`);

        // Get answer from API
        const answer = await getAnswerFromAPI(
            question.questionText,
            question.options,
            question.questionType
        );

        if (answer) {
            const optionEl = findOptionElement(answer);
            if (optionEl) {
                optionEl.click();
                updateStatus(`Clicked: ${answer.substring(0, 30)}...`);
            } else {
                updateStatus(`Found answer but couldn't click: ${answer.substring(0, 30)}...`);
            }
        }

        // Find and click Next button
        setTimeout(async () => {
            const nextBtn = document.querySelector('button:has-text("Next"), button[data-automation-id*="next"]');
            if (nextBtn) {
                nextBtn.click();
            }

            // Continue to next question
            if (isRunning) {
                setTimeout(solveNextQuestion, questionDelay);
            }
        }, 1500);
    }

    function startSolving() {
        saveConfig();

        if (!apiKey && !userId) {
            alert('Please enter an API key or User ID');
            return;
        }

        isRunning = true;
        document.getElementById('qg-start').style.display = 'none';
        document.getElementById('qg-stop').style.display = 'block';
        updateStatus('Starting...');
        solveNextQuestion();

        GM_notification({
            title: 'QuizGenius',
            text: 'Started solving your quiz!',
            timeout: 3
        });
    }

    function stopSolving() {
        isRunning = false;
        document.getElementById('qg-start').style.display = 'block';
        document.getElementById('qg-stop').style.display = 'none';
        updateStatus('Stopped');

        GM_notification({
            title: 'QuizGenius',
            text: 'Stopped solving',
            timeout: 3
        });
    }

    // Initialize
    function init() {
        // Wait for page to load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        // Only create panel on McGraw Hill domains
        if (window.location.hostname.includes('mheducation') ||
            window.location.hostname.includes('connect.mh') ||
            window.location.hostname.includes('learning.mheducation')) {
            createControlPanel();
        }
    }

    init();
})();
