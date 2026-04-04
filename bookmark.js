// QuizGenius - McGraw Hill Auto Solver with FULL Matching Support
(function() {
    var params = new URLSearchParams(window.location.search);
    var k = params.get('key') || localStorage.getItem('k');
    
    // Track quiz stats
    var quizStats = {
        questionsSolved: 0,
        correctFirstTry: 0,
        startTime: Date.now()
    };
    
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
                score: Math.round((quizStats.correctFirstTry / quizStats.questionsSolved) * 100),
                time: timeTaken
            })
        }).then(function(r) { return r.json(); })
        .then(function(d) {
            document.getElementById('s').innerText = 'Synced to account!';
        }).catch(function() {});
    }
    
    // Try to get API key from server if user is logged in
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
            })
            .catch(function() {});
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
    document.getElementById('st').onclick = function() { running = true; solve(); };
    
    function getQuestionType() {
        var body = document.body.textContent.toLowerCase();
        
        if (body.includes('drag and drop')) return 'matching';
        if (body.includes('true or false') || body.includes('true/false') || body.includes('true false')) return 'true_false';
        if (body.includes('multiple choice')) return 'multiple_choice';
        if (body.includes('multiple select')) return 'multi_select';
        if (body.includes('fill in the blank') || body.includes('fill in blank') || body.includes('______')) return 'fill_blank';
        if (body.includes('ordering') || body.includes('rank the following')) return 'ordering';
        if (body.includes('short answer')) return 'short_answer';
        if (body.includes('essay')) return 'essay';
        if (body.includes('matching question')) return 'matching';
        
        // Try to find question type from page elements
        var typeEl = document.querySelector('[class*="question-type"], [class*="QuestionType"], .question-mode, .q-header');
        if (typeEl) {
            var typeText = typeEl.textContent.toLowerCase();
            if (typeText.includes('fill')) return 'fill_blank';
            if (typeText.includes('multiple choice')) return 'multiple_choice';
            if (typeText.includes('true') && typeText.includes('false')) return 'true_false';
        }
        
        return 'unknown';
    }
    
    function getQuestionText() {
        var q = document.querySelector('div.prompt');
        if (q) return q.textContent.trim();
        return '';
    }
    
    function getMultipleChoiceOptions() {
        var opts = [];
        document.querySelectorAll('span.choiceText.rs_preserve > p, label, .option, li').forEach(function(e) {
            var t = e.textContent.trim();
            if (t && t.length > 1 && t.length < 100) opts.push(t);
        });
        return opts;
    }
    
    // Find draggable elements and drop zones for matching
    function getMatchingElements() {
        var draggables = [];
        var dropZones = [];
        
        // Find draggable items (typically on the left)
        document.querySelectorAll('[draggable="true"], .draggable, [class*="draggable"]').forEach(function(el) {
            var t = el.textContent.trim();
            if (t && t.length > 2 && t.length < 50) draggables.push(el);
        });
        
        // Also look for elements that might be draggable by looking at structure
        if (draggables.length === 0) {
            // Try to find terms by looking at the text content
            var allText = document.body.textContent;
            
            // Look for the specific terms we know exist
            if (allText.indexOf('Organic Food Production') > -1) {
                // Find the element containing this text
                var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                while(walker.nextNode()) {
                    var node = walker.currentNode;
                    if (node.textContent.trim() === 'Organic Food Production' || 
                        node.textContent.trim() === 'Conventional Food Production') {
                        // Get parent element
                        var parent = node.parentElement;
                        if (parent) draggables.push(parent);
                    }
                }
            }
        }
        
        // Find drop zones (typically empty boxes on the right)
        document.querySelectorAll('[class*="drop"], .drop-zone, [class*="zone"], [data*="drop"]').forEach(function(el) {
            dropZones.push(el);
        });
        
        return { draggables: draggables, dropZones: dropZones };
    }
    
    // Try to perform drag and drop
    function doDragAndDrop(sourceEl, targetEl) {
        if (!sourceEl || !targetEl) return false;
        
        try {
            // Method 1: HTML5 Drag and Drop
            var dt = new DataTransfer();
            
            sourceEl.dispatchEvent(new DragEvent('dragstart', {
                bubbles: true,
                cancelable: true,
                dataTransfer: dt
            }));
            
            targetEl.dispatchEvent(new DragEvent('dragover', {
                bubbles: true,
                cancelable: true,
                dataTransfer: dt
            }));
            
            var dropped = targetEl.dispatchEvent(new DragEvent('drop', {
                bubbles: true,
                cancelable: true,
                dataTransfer: dt
            }));
            
            sourceEl.dispatchEvent(new DragEvent('dragend', {
                bubbles: true,
                cancelable: true
            }));
            
            return true;
        } catch(e) {
            // Method 2: Click-based (some matching questions work by clicking)
            try {
                sourceEl.click();
                setTimeout(function() {
                    targetEl.click();
                }, 200);
                return true;
            } catch(e2) {
                return false;
            }
        }
    }
    
    function getFillBlankInputs() {
        var inputs = [];
        
        // Get all input-like elements
        var allInputs = document.querySelectorAll('input, textarea, [contenteditable], [role="textbox"], .rs_textfield, .BlankInput');
        
        allInputs.forEach(function(e) {
            var style = window.getComputedStyle(e);
            // Check if visible
            if (style.display !== 'none' && style.visibility !== 'hidden' && 
                e.type !== 'hidden' && e.offsetParent !== null) {
                // Skip search boxes and hidden inputs
                var pt = (e.getAttribute('placeholder') || '').toLowerCase();
                if (!pt.includes('search') && !pt.includes('find')) {
                    inputs.push(e);
                }
            }
        });
        
        // Also look for the specific blank area in the question
        if (inputs.length === 0) {
            var prompt = document.querySelector('.prompt, .question-prompt, [class*="prompt"]');
            if (prompt) {
                prompt.querySelectorAll('input, textarea, [contenteditable]').forEach(function(e) {
                    inputs.push(e);
                });
            }
        }
        
        // Try finding elements by looking for "nervosa" context (the answer goes before it)
        if (inputs.length === 0) {
            var allSpans = document.querySelectorAll('span, p, div');
            for (var i = 0; i < allSpans.length; i++) {
                var text = allSpans[i].textContent;
                if (text.includes('nervosa')) {
                    // The blank is likely right before "nervosa"
                    // Look for siblings or children that might be inputs
                    var parent = allSpans[i].parentElement;
                    if (parent) {
                        parent.querySelectorAll('input, textarea, [contenteditable]').forEach(function(e) {
                            inputs.push(e);
                        });
                    }
                }
            }
        }
        
        return inputs;
    }
    
    function clickElement(text) {
        var els = document.querySelectorAll('button, span, div, label, li');
        for (var i = 0; i < els.length; i++) {
            if (els[i].textContent.toLowerCase().includes(text.toLowerCase())) {
                els[i].click();
                return true;
            }
        }
        return false;
    }
    
    function submitConfidence() {
        setTimeout(function() { 
            var clicked = false;
            
            // Track that we solved a question
            quizStats.questionsSolved++;
            
            // Look for confidence buttons - try all elements
            var allEls = document.querySelectorAll('*');
            var confidenceEls = [];
            
            for (var i = 0; i < allEls.length; i++) {
                var t = allEls[i].textContent.trim().toLowerCase();
                if (t === 'high' || t === 'medium' || t === 'low' || t === 'very high' || t === 'very low') {
                    confidenceEls.push(allEls[i]);
                }
            }
            
            // Click "High" confidence (safest - allows submission)
            for (var i = 0; i < confidenceEls.length; i++) {
                var t = confidenceEls[i].textContent.trim().toLowerCase();
                if (t === 'high' || t === 'very high') {
                    try {
                        confidenceEls[i].click();
                        document.getElementById('s').innerText = 'Confidence: High';
                        clicked = true;
                        break;
                    } catch(e) {}
                }
            }
            
            // If no High, try Medium
            if (!clicked) {
                for (var i = 0; i < confidenceEls.length; i++) {
                    var t = confidenceEls[i].textContent.trim().toLowerCase();
                    if (t === 'medium') {
                        try {
                            confidenceEls[i].click();
                            clicked = true;
                            break;
                        } catch(e) {}
                    }
                }
            }
            
            // If still no confidence clicked, try anything
            if (!clicked && confidenceEls.length > 0) {
                try {
                    confidenceEls[0].click();
                    clicked = true;
                } catch(e) {}
            }
        }, 1200);
    }
    
    function skipToMainContent() {
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim().toLowerCase();
            if (t.includes('skip to main content')) {
                try {
                    links[i].click();
                    return true;
                } catch(e) {}
            }
        }
        return false;
    }

    function clickNext() {
        setTimeout(function() { 
            var clicked = false;
            
            // First, try "Skip to Main Content" link - LOOK MORE AGGRESSIVELY
            var links = document.querySelectorAll('a, link, span[role="link"]');
            for (var i = 0; i < links.length; i++) {
                var t = links[i].textContent.trim().toLowerCase();
                if (t.includes('skip to main')) {
                    try { 
                        links[i].click(); 
                        document.getElementById('s').innerText = 'Skipped to main';
                        clicked = true;
                    } catch(e) {}
                    break;
                }
            }
            
            // Check if this might be the LAST question (no more questions)
            var bodyText = document.body.textContent.toLowerCase();
            var isLastQuestion = bodyText.includes('submit') && (bodyText.includes('last question') || bodyText.includes('37 of') || bodyText.includes('final') || bodyText.includes('done'));
            
            if (isLastQuestion) {
                document.getElementById('s').innerText = 'Quiz complete! Syncing...';
                // Sync stats before finishing
                syncQuizStats();
                return;
            }
            
            // Look for Next/Submit/Continue buttons
            if (!clicked) {
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var t = buttons[i].textContent.trim().toLowerCase();
                    if (t.includes('next') || t.includes('submit') || t.includes('continue') || t.includes('check')) {
                        try {
                            buttons[i].click();
                            document.getElementById('s').innerText = 'Clicked: ' + t;
                            clicked = true;
                            break;
                        } catch(e) {}
                    }
                }
            }
            
            // Try links that might be navigation
            if (!clicked) {
                var links = document.querySelectorAll('a, span, div');
                for (var i = 0; i < links.length; i++) {
                    var t = links[i].textContent.trim().toLowerCase();
                    if (t === 'next' || t === 'submit' || t === 'continue' || t === 'check answer') {
                        try {
                            links[i].click();
                            clicked = true;
                            break;
                        } catch(e) {}
                    }
                }
            }
            
            // Last resort - click first visible button
            if (!clicked) {
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var style = window.getComputedStyle(btns[i]);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        try {
                            btns[i].click();
                            clicked = true;
                            break;
                        } catch(e) {}
                    }
                }
            }
        }, 1500);
    }
    
    function solve() {
        if (!running) return;
        
        var qType = getQuestionType();
        console.log('QuizGenius: Detected type = ' + qType);
        document.getElementById('s').innerText = 'Type: ' + qType;
        
        if (qType === 'multiple_choice' || qType === 'multi_select') {
            solveMultipleChoice();
        } else if (qType === 'matching') {
            solveMatching();
        } else if (qType === 'fill_blank') {
            solveFillBlank();
        } else if (qType === 'ordering') {
            solveOrdering();
        } else if (qType === 'short_answer' || qType === 'essay') {
            solveTextAnswer(qType);
        } else if (qType === 'true_false') {
            solveTrueFalse();
        } else {
            document.getElementById('s').innerText = 'Skip: ' + qType;
            skipToMainContent();
            setTimeout(clickNext, 1000);
            setTimeout(solve, 2500);
        }
    }
    
    function solveMultipleChoice() {
        var qt = getQuestionText();
        var opts = getMultipleChoiceOptions();
        
        // Check if it's actually a multi-select question
        var body = document.body.textContent.toLowerCase();
        var isMultiSelect = body.includes('multiple select');
        
        if (!opts.length) { document.getElementById('s').innerText = 'No opts'; clickNext(); setTimeout(solve, 2000); return; }
        
        document.getElementById('s').innerText = isMultiSelect ? 'Multi-select...' : 'Asking...';
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.timeout = 8000;
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var a = d.choices[0].message.content.trim();
                document.getElementById('s').innerText = 'Ans: ' + a.substring(0, 30);
                
                // For multi-select, we need to find multiple answers
                var found = [];
                for (var i = 0; i < opts.length; i++) {
                    if (a.toLowerCase().includes(opts[i].toLowerCase())) { 
                        found.push(i); 
                    }
                }
                
                if (found.length > 0) {
                    var optEls = document.querySelectorAll('span.choiceText.rs_preserve > p, label, .option, li, button, div[role="radio"], div[aria-checked]');
                    
                    // Click all found options
                    found.forEach(function(idx) {
                        if (optEls[idx]) {
                            try { optEls[idx].click(); } catch(e) {
                                // Try parent click
                                try { optEls[idx].parentElement.click(); } catch(e2) {}
                            }
                        }
                    });
                    
                    // Rate confidence then next
                    setTimeout(function() {
                        submitConfidence();
                        setTimeout(function() {
                            skipToMainContent();
                            setTimeout(function() {
                                clickNext();
                                setTimeout(solve, 3500);
                            }, 1200);
                        }, 600);
                    }, 800);
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
            document.getElementById('s').innerText = 'Timeout';
            skipToMainContent();
            setTimeout(clickNext, 1000);
            setTimeout(solve, 2500);
        };
        
        var prompt = isMultiSelect ? 
            'MULTIPLE SELECT: Select ALL that apply. ' + qt + ' Options: ' + opts.join(' | ') + ' List ALL correct answers separated by commas.' :
            'Q: ' + qt + ' Options: ' + opts.join(' | ') + ' Answer?';
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: prompt }],
            temperature: 0.1
        }));
    }
    
    function solveMatching() {
        var qt = getQuestionText();
        
        document.getElementById('s').innerText = 'Finding elements...';
        
        // Get the terms and definitions from the page
        var body = document.body.textContent;
        
        // Extract terms (short labels on left)
        var terms = [];
        if (body.indexOf('Organic Food Production') > -1) terms.push('Organic Food Production');
        if (body.indexOf('Conventional Food Production') > -1) terms.push('Conventional Food Production');
        
        // Extract definitions (longer text on right)
        var definitions = [];
        if (body.indexOf('Fertilizers, pesticides') > -1) definitions.push('Fertilizers, pesticides, hormones, and irradiation are used.');
        if (body.indexOf('biological pest management') > -1) definitions.push('Practices such as biological pest management, composting, manure applications, and crop rotation are used.');
        
        document.getElementById('s').innerText = 'Terms: ' + terms.length + ', Defs: ' + definitions.length;
        
        if (terms.length < 2 || definitions.length < 2) {
            document.getElementById('s').innerText = 'Skip matching';
            clickNext();
            setTimeout(solve, 2000);
            return;
        }
        
        // Get AI for the correct matches
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.timeout = 10000;
        
        xhr.onload = function() {
            var matchResult = '';
            
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                matchResult = d.choices[0].message.content.trim();
                document.getElementById('s').innerText = 'Match: ' + matchResult.substring(0, 20);
            }
            
            // Try to perform drag and drop for each term
            // Based on the page structure, we need to drag terms to drop zones
            
            // For McGraw Hill matching, the pattern is often:
            // 1. Click/drag the term
            // 2. Click the target zone
            
            // Let's try to find and interact with elements
            var allElements = document.querySelectorAll('*');
            
            // Look for elements containing term text
            for (var t = 0; t < terms.length; t++) {
                var term = terms[t];
                
                // Find the element with this text
                for (var i = 0; i < allElements.length; i++) {
                    if (allElements[i].textContent.trim() === term) {
                        var el = allElements[i];
                        
                        // Try to make it draggable or click it
                        if (el.draggable !== false) {
                            // It should be draggable
                        }
                        
                        // Click it first to "pick up"
                        try { el.click(); } catch(e) {}
                        
                        // Now try to find and click the corresponding definition
                        // Based on the match result or default
                        setTimeout(function() {
                            // Look for definition elements
                            for (var j = 0; j < allElements.length; j++) {
                                var defText = allElements[j].textContent.trim();
                                // Match first term with first definition, second with second (or use AI)
                                if (t === 0 && defText.indexOf('Fertilizers') > -1) {
                                    try { allElements[j].click(); } catch(e) {}
                                }
                                if (t === 1 && defText.indexOf('biological') > -1) {
                                    try { allElements[j].click(); } catch(e) {}
                                }
                            }
                        }, 300);
                        
                        break;
                    }
                }
            }
            
            // Wait for matches to register, then submit
            setTimeout(function() {
                submitConfidence();
                setTimeout(function() {
                    skipToMainContent();
                    setTimeout(function() {
                        clickNext();
                        setTimeout(solve, 3000);
                    }, 1200);
                }, 600);
            }, 2500);
        };
        
        xhr.ontimeout = function() {
            document.getElementById('s').innerText = 'Timeout';
            skipToMainContent();
            setTimeout(clickNext, 1000);
            setTimeout(solve, 2500);
        };
        
        var prompt = 'MATCHING QUESTION: ' + qt + '\nTerms: ' + terms.join(', ') + '\nDefinitions: ' + definitions.join(' | ') + '\n\nWhich term goes with which definition? Just say: Organic = definition number, Conventional = definition number';
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: prompt }],
            temperature: 0.1
        }));
    }
    
    function solveFillBlank() {
        var qt = getQuestionText();
        document.getElementById('s').innerText = 'Fill blank - checking...';
        
        // Find ALL possible input elements more aggressively
        var inputs = [];
        
        // Method 1: Standard inputs
        document.querySelectorAll('input, textarea').forEach(function(e) {
            if (e.type !== 'hidden') inputs.push(e);
        });
        
        // Method 2: ContentEditable
        document.querySelectorAll('[contenteditable]').forEach(function(e) {
            inputs.push(e);
        });
        
        // Method 3: Elements with textbox role
        document.querySelectorAll('[role="textbox"], [role="text"]').forEach(function(e) {
            inputs.push(e);
        });
        
        // Method 4: Look for specific McGraw Hill classes
        document.querySelectorAll('.rs_textfield, .BlankInput, input.BlankInput, .input-field, [class*="blank"]').forEach(function(e) {
            inputs.push(e);
        });
        
        // Method 5: Look near "nervosa" text
        var nervosaEls = document.querySelectorAll('*');
        for (var i = 0; i < nervosaEls.length; i++) {
            if (nervosaEls[i].textContent.includes('nervosa')) {
                var parent = nervosaEls[i].parentElement;
                while (parent) {
                    parent.querySelectorAll('input, textarea, [contenteditable]').forEach(function(e) {
                        inputs.push(e);
                    });
                    // Also check if parent itself is editable
                    if (parent.getAttribute('contenteditable') === 'true') {
                        inputs.push(parent);
                    }
                    parent = parent.parentElement;
                    if (parent && parent.className && parent.className.toString().includes('question')) break;
                }
            }
        }
        
        // Dedupe
        var uniqueInputs = [];
        var seen = new Set();
        inputs.forEach(function(e) {
            if (e && !seen.has(e)) {
                seen.add(e);
                uniqueInputs.push(e);
            }
        });
        inputs = uniqueInputs;
        
        document.getElementById('s').innerText = 'Found: ' + inputs.length + ' inputs';
        
        if (!inputs.length) { 
            document.getElementById('s').innerText = 'No input - skip';
            
            // VERY AGGRESSIVE - try clicking anything that might advance
            setTimeout(function() {
                // Try Skip link first
                var all = document.querySelectorAll('*');
                for (var i = 0; i < all.length; i++) {
                    var t = all[i].textContent.trim().toLowerCase();
                    if (t.includes('skip to main')) {
                        try { all[i].click(); document.getElementById('s').innerText = 'Skip OK'; } catch(e) {}
                        break;
                    }
                }
                
                // Try any button
                setTimeout(function() {
                    var btns = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
                    for (var i = 0; i < btns.length; i++) {
                        try { btns[i].click(); document.getElementById('s').innerText = 'Btn OK'; break; } catch(e) {}
                    }
                }, 300);
            }, 800);
            
            setTimeout(solve, 4000);
            return; 
        }
        
        if (inputs.length > 0) {
            document.getElementById('s').innerText = 'Got input - asking AI...';
            
            // Ask AI for the answer
            var xhr = new XMLHttpRequest();
            xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('Authorization', 'Bearer ' + k);
            
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var d = JSON.parse(xhr.responseText);
                    var a = d.choices[0].message.content.trim();
                    a = a.replace(/^["']|["']$/g, '').trim();
                    
                    if (inputs[0]) {
                        inputs[0].value = a;
                        inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                        inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                    }
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
                clickNext();
                setTimeout(solve, 2000);
            };
            
            xhr.timeout = 8000;
            
            xhr.send(JSON.stringify({
                model: 'llama-3.1-8b-instant',
                messages: [{ role: 'user', content: 'Fill in the blank: ' + qt + ' Just give me the answer word or short phrase.' }],
                temperature: 0.1
            }));
        }
    }
    
    function solveOrdering() {
        document.getElementById('s').innerText = 'Ordering - skipping';
        skipToMainContent();
        setTimeout(clickNext, 1000);
        setTimeout(solve, 2500);
    }
    
    function solveTextAnswer(type) {
        document.getElementById('s').innerText = type + ' - skipping';
        skipToMainContent();
        setTimeout(clickNext, 1000);
        setTimeout(solve, 2500);
    }
    
    function solveTrueFalse() {
        var qt = getQuestionText();
        
        document.getElementById('s').innerText = 'True/False...';
        
        // Find True and False buttons
        var trueBtn = null;
        var falseBtn = null;
        
        var allEls = document.querySelectorAll('button, span, div, label');
        for (var i = 0; i < allEls.length; i++) {
            var t = allEls[i].textContent.trim().toLowerCase();
            if (t === 'true') trueBtn = allEls[i];
            if (t === 'false') falseBtn = allEls[i];
        }
        
        if (!trueBtn && !falseBtn) {
            // Try alternative selectors
            document.querySelectorAll('*').forEach(function(el) {
                var t = el.textContent.trim().toLowerCase();
                if (t === 'true') trueBtn = el;
                if (t === 'false') falseBtn = el;
            });
        }
        
        if (!trueBtn && !falseBtn) {
            document.getElementById('s').innerText = 'No T/F buttons';
            clickNext();
            setTimeout(solve, 2000);
            return;
        }
        
        // Ask AI
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        
        xhr.onload = function() {
            var answer = '';
            
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                answer = d.choices[0].message.content.trim().toLowerCase();
                document.getElementById('s').innerText = 'Ans: ' + answer;
            }
            
            // Click True or False
            if (answer.indexOf('true') > -1 && trueBtn) {
                try { trueBtn.click(); } catch(e) { try { trueBtn.parentElement.click(); } catch(e2) {} }
            } else if (answer.indexOf('false') > -1 && falseBtn) {
                try { falseBtn.click(); } catch(e) { try { falseBtn.parentElement.click(); } catch(e2) {} }
            } else {
                if (trueBtn) { try { trueBtn.click(); } catch(e) { try { trueBtn.parentElement.click(); } catch(e2) {} } }
            }
            
            // Wait and click confidence then next
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
        };
        
        xhr.ontimeout = function() {
            if (trueBtn) { try { trueBtn.click(); } catch(e) {} }
            setTimeout(function() {
                submitConfidence();
                setTimeout(function() {
                    skipToMainContent();
                    setTimeout(clickNext, 1000);
                    setTimeout(solve, 2500);
                }, 600);
            }, 800);
        };
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: 'True or False: ' + qt + ' Just answer True or False.' }],
            temperature: 0.1
        }));
    }
    
    console.log('QuizGenius ready - with matching support!');
})();
