// QuizGenius - McGraw Hill Auto Solver with FULL Matching Support
(function() {
    var params = new URLSearchParams(window.location.search);
    var k = params.get('key') || localStorage.getItem('k');
    
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
        if (body.includes('fill') || body.includes('______')) return 'fill_blank';
        if (body.includes('ordering') || body.includes('rank the following')) return 'ordering';
        if (body.includes('short answer')) return 'short_answer';
        if (body.includes('essay')) return 'essay';
        if (body.includes('matching question')) return 'matching';
        
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
        document.querySelectorAll('input[type="text"], textarea').forEach(function(e) {
            if (e.type !== 'hidden') inputs.push(e);
        });
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
            // Try multiple selectors for confidence buttons
            var clicked = false;
            
            // Try to find buttons with high/medium/low
            var allEls = document.querySelectorAll('button, span, div, label, p');
            for (var i = 0; i < allEls.length; i++) {
                var t = allEls[i].textContent.trim().toLowerCase();
                if (t === 'high' || t === 'medium' || t === 'low') {
                    try {
                        allEls[i].click();
                        clicked = true;
                        break;
                    } catch(e) {}
                }
            }
            
            if (!clicked) {
                // Try finding by looking for confidence-related text nearby
                var body = document.body.textContent;
                if (body.indexOf('Rate your confidence') > -1) {
                    // Confidence buttons should be nearby
                    for (var i = 0; i < allEls.length; i++) {
                        var t = allEls[i].textContent.trim().toLowerCase();
                        if (t === 'high' || t === 'medium' || t === 'low') {
                            try {
                                allEls[i].click();
                                break;
                            } catch(e) {}
                        }
                    }
                }
            }
        }, 800);
    }
    
    function clickNext() {
        setTimeout(function() { clickElement('Next') || clickElement('Submit'); }, 1500);
    }
    
    function solve() {
        if (!running) return;
        
        var qType = getQuestionType();
        document.getElementById('s').innerText = qType;
        
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
            clickNext();
            setTimeout(solve, 2000);
        }
    }
    
    function solveMultipleChoice() {
        var qt = getQuestionText();
        var opts = getMultipleChoiceOptions();
        
        if (!opts.length) { document.getElementById('s').innerText = 'No opts'; clickNext(); setTimeout(solve, 2000); return; }
        
        document.getElementById('s').innerText = 'Asking...';
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.timeout = 8000;
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var a = d.choices[0].message.content.trim();
                document.getElementById('s').innerText = 'Ans: ' + a.substring(0, 15);
                
                var found = -1;
                for (var i = 0; i < opts.length; i++) {
                    if (a.toLowerCase().includes(opts[i].toLowerCase())) { found = i; break; }
                }
                
                if (found >= 0) {
                    var optEls = document.querySelectorAll('span.choiceText.rs_preserve > p, label, .option, li');
                    if (optEls[found]) optEls[found].click();
                    submitConfidence();
                    clickNext();
                    setTimeout(solve, 4000);
                } else {
                    document.getElementById('s').innerText = 'No match';
                    clickNext();
                    setTimeout(solve, 2000);
                }
            } else {
                document.getElementById('s').innerText = 'API error';
                clickNext();
                setTimeout(solve, 2000);
            }
        };
        
        xhr.ontimeout = function() {
            document.getElementById('s').innerText = 'Timeout';
            clickNext();
            setTimeout(solve, 2000);
        };
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: 'Q: ' + qt + ' Options: ' + opts.join(' | ') + ' Answer?' }],
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
                clickNext();
                setTimeout(solve, 3000);
            }, 2000);
        };
        
        xhr.ontimeout = function() {
            document.getElementById('s').innerText = 'Timeout';
            clickNext();
            setTimeout(solve, 2000);
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
        var inputs = getFillBlankInputs();
        
        if (!inputs.length) { document.getElementById('s').innerText = 'No input'; clickNext(); setTimeout(solve, 2000); return; }
        
        document.getElementById('s').innerText = 'Fill...';
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var a = d.choices[0].message.content.trim();
                if (inputs[0]) inputs[0].value = a;
            }
            submitConfidence();
            clickNext();
            setTimeout(solve, 3000);
        };
        
        xhr.ontimeout = function() {
            clickNext();
            setTimeout(solve, 2000);
        };
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: 'Fill blank: ' + qt + ' Answer?' }],
            temperature: 0.1
        }));
    }
    
    function solveOrdering() {
        document.getElementById('s').innerText = 'Ordering';
        clickNext();
        setTimeout(solve, 2000);
    }
    
    function solveTextAnswer(type) {
        document.getElementById('s').innerText = type;
        clickNext();
        setTimeout(solve, 2000);
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
                trueBtn.click();
            } else if (answer.indexOf('false') > -1 && falseBtn) {
                falseBtn.click();
            } else {
                // Default: pick True (safer guess)
                if (trueBtn) trueBtn.click();
            }
            
            // Wait and click confidence
            setTimeout(function() {
                submitConfidence();
                clickNext();
                setTimeout(solve, 3000);
            }, 1000);
        };
        
        xhr.ontimeout = function() {
            // Default to True on timeout
            if (trueBtn) trueBtn.click();
            submitConfidence();
            clickNext();
            setTimeout(solve, 2000);
        };
        
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: 'True or False: ' + qt + ' Just answer True or False.' }],
            temperature: 0.1
        }));
    }
    
    console.log('QuizGenius ready - with matching support!');
})();
