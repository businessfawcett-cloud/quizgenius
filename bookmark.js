// QuizGenius - McGraw Hill Auto Solver
(function() {
    var params = new URLSearchParams(window.location.search);
    var k = params.get('key') || localStorage.getItem('k');
    
    var quizStats = { questionsSolved: 0, correctFirstTry: 0, startTime: Date.now() };
    
    function syncQuizStats() {
        var timeTaken = Math.round((Date.now() - quizStats.startTime) / 1000);
        fetch('https://quizgenius-nji8.onrender.com/api/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: localStorage.getItem('user_id'),
                action: 'record_quiz',
                questions: quizStats.questionsSolved,
                correct: quizStats.correctFirstTry,
                score: quizStats.questionsSolved > 0 ? Math.round((quizStats.correctFirstTry / quizStats.questionsSolved) * 100) : 0,
                time: timeTaken
            })
        }).catch(function() {});
    }
    
    if (!k) {
        fetch('https://quizgenius-nji8.onrender.com/api/key')
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d.api_key) {
                    k = d.api_key;
                    localStorage.setItem('k', k);
                    localStorage.setItem('user_id', d.user_id);
                    document.getElementById('s').innerText = 'Key loaded from account';
                }
            }).catch(function() {});
    }
    
    if (!k) {
        k = prompt('Enter API Key (get free at console.groq.com/keys):');
        if (k) localStorage.setItem('k', k);
    }
    
    if (!k) { alert('API key required!'); return; }
    
    var p = document.createElement('div');
    p.style.cssText = 'position:fixed;top:10px;right:10px;z-index:99999;background:#222;padding:15px;border-radius:10px;color:#fff;font-family:sans-serif;min-width:200px;';
    p.innerHTML = '<b style="color:#0f8">QuizGenius</b><br><span id=s style="font-size:12px">Ready</span><br><button id=st style="background:#0f8;padding:8px 16px;border:none;border-radius:5px;cursor:pointer;margin-top:8px">Start</button>';
    document.body.appendChild(p);
    
    var running = false;
    var btn = document.getElementById('st');
    
    btn.onclick = function() { 
        if (!running) {
            running = true;
            btn.textContent = 'Stop';
            btn.style.background = '#f44';
            btn.style.color = '#fff';
            solve();
        } else {
            running = false;
            btn.textContent = 'Start';
            btn.style.background = '#0f8';
            btn.style.color = '#000';
            document.getElementById('s').innerText = 'Stopped';
        }
    };
    
    function getQuestionType() {
        var body = document.body.textContent.toLowerCase();
        if (body.includes('drag and drop')) return 'matching';
        if (body.includes('true or false') || body.includes('true/false')) return 'true_false';
        if (body.includes('multiple select')) return 'multi_select';
        if (body.includes('multiple choice')) return 'multiple_choice';
        if (body.includes('fill in the blank') || body.includes('______')) return 'fill_blank';
        if (body.includes('ordering') || body.includes('rank the following')) return 'ordering';
        if (body.includes('short answer')) return 'short_answer';
        if (body.includes('essay')) return 'essay';
        if (body.includes('matching question')) return 'matching';
        return 'unknown';
    }
    
    function getQuestionText() {
        var q = document.querySelector('div.prompt, .question-prompt, [class*="prompt"], [class*="question"]');
        return q ? q.textContent.trim() : document.body.textContent.substring(0, 500);
    }
    
    function getMultipleChoiceOptions() {
        var opts = [];
        document.querySelectorAll('span.choiceText.rs_preserve > p, label, .option, li, button, div[role="radio"]').forEach(function(e) {
            var t = e.textContent.trim();
            if (t && t.length > 1 && t.length < 200) opts.push(t);
        });
        var unique = [];
        var seen = {};
        opts.forEach(function(o) { if (!seen[o]) { seen[o] = true; unique.push(o); } });
        return unique;
    }
    
    function submitConfidence() {
        setTimeout(function() {
            quizStats.questionsSolved++;
            var allEls = document.querySelectorAll('*');
            var confidenceEls = [];
            for (var i = 0; i < allEls.length; i++) {
                var t = allEls[i].textContent.trim().toLowerCase();
                if (t === 'high' || t === 'medium' || t === 'low') confidenceEls.push(allEls[i]);
            }
            for (var i = 0; i < confidenceEls.length; i++) {
                if (confidenceEls[i].textContent.trim().toLowerCase() === 'high') {
                    try { confidenceEls[i].click(); break; } catch(e) {}
                }
            }
        }, 800);
    }
    
    function skipToMainContent() {
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
            if (links[i].textContent.trim().toLowerCase().includes('skip to main')) {
                try { links[i].click(); return true; } catch(e) {}
            }
        }
        return false;
    }
    
    function clickNext() {
        setTimeout(function() {
            var clicked = false;
            skipToMainContent();
            
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var t = buttons[i].textContent.trim().toLowerCase();
                if (t.includes('next') || t.includes('submit') || t.includes('continue')) {
                    try { buttons[i].click(); clicked = true; break; } catch(e) {}
                }
            }
            
            if (!clicked) {
                var radios = document.querySelectorAll('input[type="radio"]');
                for (var i = 0; i < radios.length; i++) {
                    try { radios[i].click(); clicked = true; break; } catch(e) {}
                }
            }
        }, 1500);
    }
    
    function solve() {
        if (!running) return;
        var qType = getQuestionType();
        document.getElementById('s').innerText = 'Type: ' + qType;
        
        if (qType === 'multiple_choice' || qType === 'multi_select') solveMultipleChoice();
        else if (qType === 'true_false') solveTrueFalse();
        else if (qType === 'fill_blank') solveFillBlank();
        else if (qType === 'matching') solveMatching();
        else {
            document.getElementById('s').innerText = 'Skip: ' + qType;
            skipToMainContent();
            setTimeout(clickNext, 1000);
            setTimeout(solve, 2500);
        }
    }
    
    function solveMultipleChoice() {
        var qt = getQuestionText();
        var opts = getMultipleChoiceOptions();
        var body = document.body.textContent.toLowerCase();
        var isMultiSelect = body.includes('multiple select');
        
        if (!opts.length) { document.getElementById('s').innerText = 'No opts'; clickNext(); setTimeout(solve, 2000); return; }
        
        document.getElementById('s').innerText = isMultiSelect ? 'Multi-select...' : 'Asking...';
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.timeout = 8000;
        
        var prompt = isMultiSelect ?
            'MULTIPLE SELECT - select ALL that apply. Question: ' + qt + ' Options: ' + opts.join(' | ') + ' List the correct answers separated by commas.' :
            'Question: ' + qt + ' Options: ' + opts.join(' | ') + ' Choose the SINGLE correct answer. Just say the answer word.';
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var a = d.choices[0].message.content.trim();
                document.getElementById('s').innerText = 'Ans: ' + a.substring(0, 30);
                
                var found = [];
                var lowerOpts = opts.map(function(o) { return o.toLowerCase().trim(); });
                var lowerA = a.toLowerCase().trim();
                
                if (isMultiSelect) {
                    // For multi-select, be VERY strict - only match if option appears verbatim in answer
                    for (var i = 0; i < opts.length; i++) {
                        // Check if the exact option text appears in the AI response
                        if (lowerA.includes(lowerOpts[i])) {
                            found.push(i);
                        }
                        // Also check if most of the option words appear together
                        else {
                            var optWords = lowerOpts[i].split(/\s+/).filter(function(w) { return w.length > 3; });
                            var consecutiveMatch = 0;
                            for (var w = 0; w < optWords.length; w++) {
                                if (lowerA.includes(optWords[w])) consecutiveMatch++;
                            }
                            // Require 90%+ of significant words to match
                            if (consecutiveMatch >= optWords.length * 0.9 && optWords.length > 0) {
                                found.push(i);
                            }
                        }
                    }
                } else {
                    // Single choice - use existing strategies
                    // Strategy 1: Exact match
                    for (var i = 0; i < lowerOpts.length; i++) {
                        if (lowerA === lowerOpts[i] || lowerA === '"' + lowerOpts[i] + '"') found.push(i);
                    }
                    // Strategy 2: Word match
                    if (found.length === 0) {
                        var words = lowerA.replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(function(w) { return w.length > 3; });
                        for (var i = 0; i < lowerOpts.length; i++) {
                            for (var j = 0; j < words.length; j++) {
                                if (lowerOpts[i].includes(words[j])) { found.push(i); break; }
                            }
                        }
                    }
                    // Strategy 3: Answer contains option
                    if (found.length === 0) {
                        for (var i = 0; i < lowerOpts.length; i++) {
                            if (lowerA.includes(lowerOpts[i])) found.push(i);
                        }
                    }
                }
                
                if (found.length > 0) {
                    var checkboxes = document.querySelectorAll('input[type="checkbox"]');
                    var radios = document.querySelectorAll('input[type="radio"]');
                    var labels = document.querySelectorAll('label');
                    var clicked = false;
                    
                    // For each found option, try to click it
                    found.forEach(function(idx) {
                        var answerText = opts[idx];
                        
                        // Try finding label with exact text match
                        for (var i = 0; i < labels.length; i++) {
                            var labelText = labels[i].textContent.trim();
                            if (labelText === answerText || labelText.toLowerCase() === answerText.toLowerCase()) {
                                try { labels[i].click(); clicked = true; console.log('Clicked label:', answerText); } catch(e) {}
                                break;
                            }
                        }
                        
                        // Try finding checkbox/radio whose parent contains the text
                        if (!clicked) {
                            var inputs = checkboxes.length > 0 ? checkboxes : radios;
                            for (var i = 0; i < inputs.length; i++) {
                                var parent = inputs[i].parentElement;
                                if (parent && parent.textContent.trim().toLowerCase().includes(answerText.toLowerCase())) {
                                    try { inputs[i].click(); clicked = true; console.log('Clicked input:', answerText); } catch(e) {}
                                    break;
                                }
                            }
                        }
                        
                        // Fallback: click by index
                        if (!clicked) {
                            var inputs = checkboxes.length > 0 ? checkboxes : radios;
                            if (idx < inputs.length) {
                                try { inputs[idx].click(); clicked = true; console.log('Clicked by index:', idx); } catch(e) {}
                            }
                        }
                    });
                    
                    setTimeout(function() {
                        submitConfidence();
                        setTimeout(function() {
                            skipToMainContent();
                            setTimeout(function() {
                                clickNext();
                                setTimeout(solve, 3500);
                            }, 1200);
                        }, 600);
                    }, 1000);
                } else {
                    document.getElementById('s').innerText = 'No match';
                    skipToMainContent();
                    setTimeout(clickNext, 1000);
                    setTimeout(solve, 2500);
                }
            } else {
                document.getElementById('s').innerText = 'API error';
                skipToMainContent();
                setTimeout(clickNext, 1000);
                setTimeout(solve, 2500);
            }
        };
        
        xhr.ontimeout = function() {
            skipToMainContent();
            setTimeout(clickNext, 1000);
            setTimeout(solve, 2500);
        };
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: prompt }],
            temperature: 0.1
        }));
    }
    
    function solveTrueFalse() {
        var qt = getQuestionText();
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.timeout = 8000;
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var answer = d.choices[0].message.content.trim().toLowerCase();
                document.getElementById('s').innerText = 'Ans: ' + answer.substring(0, 20);
                
                var radios = document.querySelectorAll('input[type="radio"]');
                for (var i = 0; i < radios.length; i++) {
                    var t = radios[i].parentElement.textContent.trim().toLowerCase();
                    if ((answer.includes('true') && t.includes('true')) || (answer.includes('false') && t.includes('false'))) {
                        try { radios[i].click(); break; } catch(e) {}
                    }
                }
                
                setTimeout(function() {
                    submitConfidence();
                    setTimeout(function() {
                        skipToMainContent();
                        setTimeout(function() {
                            clickNext();
                            setTimeout(solve, 3000);
                        }, 1200);
                    }, 600);
                }, 1000);
            }
        };
        
        xhr.ontimeout = function() {
            skipToMainContent();
            setTimeout(clickNext, 1000);
            setTimeout(solve, 2500);
        };
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: 'True or false: ' + qt + ' Answer true or false only.' }],
            temperature: 0.1
        }));
    }
    
    function solveFillBlank() {
        var qt = getQuestionText();
        var inputs = document.querySelectorAll('input[type="text"], textarea, [contenteditable]');
        var visibleInputs = [];
        inputs.forEach(function(e) {
            if (e.type !== 'hidden' && e.offsetParent !== null) visibleInputs.push(e);
        });
        
        if (!visibleInputs.length) {
            document.getElementById('s').innerText = 'No input';
            skipToMainContent();
            setTimeout(clickNext, 1000);
            setTimeout(solve, 2500);
            return;
        }
        
        document.getElementById('s').innerText = 'Fill blank...';
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.timeout = 8000;
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var a = d.choices[0].message.content.trim().replace(/^["']|["']$/g, '').trim();
                visibleInputs[0].value = a;
                visibleInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                visibleInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                document.getElementById('s').innerText = 'Filled: ' + a.substring(0, 15);
            }
            setTimeout(function() {
                submitConfidence();
                setTimeout(function() {
                    skipToMainContent();
                    setTimeout(function() {
                        clickNext();
                        setTimeout(solve, 3000);
                    }, 1000);
                }, 500);
            }, 1000);
        };
        
        xhr.ontimeout = function() {
            skipToMainContent();
            setTimeout(clickNext, 1000);
            setTimeout(solve, 2500);
        };
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: 'Fill in the blank: ' + qt + ' Just give the answer word or short phrase.' }],
            temperature: 0.1
        }));
    }
    
    function solveMatching() {
        document.getElementById('s').innerText = 'Matching - skipping';
        skipToMainContent();
        setTimeout(clickNext, 1000);
        setTimeout(solve, 2500);
    }
    
    function solveOrdering() {
        document.getElementById('s').innerText = 'Ordering - skipping';
        skipToMainContent();
        setTimeout(clickNext, 1000);
        setTimeout(solve, 2500);
    }
})();
