// QuizGenius - McGraw Hill Auto Solver - ALL Question Types
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
    p.innerHTML = '<b style="color:#0f8">QuizGenius</b><br><span id=s style="font-size:12px">Ready</span><br><button id=st style="background:#0f8;padding:8px 16px;border:none;border-radius:5px;cursor:pointer;margin-top:8px">Start</button><br><span id=t style="font-size:10px;color:#888">Type: -</span>';
    document.body.appendChild(p);
    
    var running = false;
    document.getElementById('st').onclick = function() { running = true; solve(); };
    
    function getQuestionType() {
        var h = document.querySelector('h1, h2, h3');
        var text = h ? h.textContent : '';
        var body = document.body.textContent;
        
        if (text.toLowerCase().includes('matching') || body.toLowerCase().includes('drag and drop')) return 'matching';
        if (text.toLowerCase().includes('multiple choice')) return 'multiple_choice';
        if (text.toLowerCase().includes('multiple select')) return 'multi_select';
        if (text.toLowerCase().includes('fill') || body.includes('______')) return 'fill_blank';
        if (text.toLowerCase().includes('ordering') || text.toLowerCase().includes('rank')) return 'ordering';
        if (text.toLowerCase().includes('short answer')) return 'short_answer';
        if (text.toLowerCase().includes('essay')) return 'essay';
        return 'unknown';
    }
    
    function getQuestionText() {
        var q = document.querySelector('div.prompt');
        if (q) return q.textContent.trim();
        var h = document.querySelector('h1, h2, h3');
        if (h) return h.textContent.trim();
        return document.body.textContent.substring(0, 500);
    }
    
    function getMultipleChoiceOptions() {
        var opts = [];
        document.querySelectorAll('span.choiceText.rs_preserve > p, label, .option, li').forEach(function(e) {
            var t = e.textContent.trim();
            if (t && t.length > 1 && t.length < 100) opts.push(t);
        });
        return opts;
    }
    
    function getMatchingPairs() {
        // Get ALL text content and parse it
        var body = document.body.textContent;
        
        // Extract terms (usually short, on the left)
        var terms = [];
        var definitions = [];
        
        // Look for the specific structure: terms like "Organic Food Production", "Conventional Food Production"
        // These appear as draggable items
        
        // Get all elements that might be terms
        document.querySelectorAll('div, span, p').forEach(function(el) {
            var t = el.textContent.trim();
            // Terms are typically short (less than 40 chars) and not sentences
            if (t && t.length > 3 && t.length < 40 && !t.includes('.') && !t.includes('?')) {
                // Check if it looks like a term (title case)
                if (t === t.replace(/\b\w/g, function(l){ return l.toUpperCase() })) {
                    if (terms.indexOf(t) === -1) terms.push(t);
                }
            }
        });
        
        // Definitions are longer text
        document.querySelectorAll('div, p, span').forEach(function(el) {
            var t = el.textContent.trim();
            // Definitions are longer sentences
            if (t && t.length > 20 && t.length < 200 && (t.includes('.') || t.includes(','))) {
                if (definitions.indexOf(t) === -1) definitions.push(t);
            }
        });
        
        // Remove duplicates and clean up
        terms = terms.slice(0, 6); // Limit terms
        definitions = definitions.slice(0, 6); // Limit definitions
        
        return { terms: terms, definitions: definitions };
    }
    
    function getFillBlankInputs() {
        var inputs = [];
        document.querySelectorAll('input[type="text"], input[placeholder*="type"], textarea').forEach(function(e) {
            if (e.type !== 'hidden') inputs.push(e);
        });
        return inputs;
    }
    
    function clickElementContaining(text) {
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
            clickElementContaining('high') || clickElementContaining('medium') || clickElementContaining('low');
        }, 500);
    }
    
    function clickNext() {
        setTimeout(function() {
            clickElementContaining('Next') || clickElementContaining('Submit');
        }, 1500);
    }
    
    function solve() {
        if (!running) return;
        
        var qType = getQuestionType();
        document.getElementById('s').innerText = qType;
        document.getElementById('t').innerText = 'Type: ' + qType;
        
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
        } else {
            document.getElementById('s').innerText = 'Unknown type';
            setTimeout(solve, 3000);
        }
    }
    
    function solveMultipleChoice() {
        var qt = getQuestionText();
        var opts = getMultipleChoiceOptions();
        
        if (!opts.length) { document.getElementById('s').innerText = 'No opts'; setTimeout(solve, 2000); return; }
        
        document.getElementById('s').innerText = 'Sending...';
        
        callAPI('Question: ' + qt + '\nOptions: ' + opts.join(' | ') + '\nWhat is the correct answer? Just say the option text nothing else.', function(a) {
            if (!a) { document.getElementById('s').innerText = 'API err'; setTimeout(solve, 2000); return; }
            
            document.getElementById('s').innerText = 'Ans: ' + a.substring(0, 20);
            
            var found = -1;
            for (var i = 0; i < opts.length; i++) {
                if (a.toLowerCase().includes(opts[i].toLowerCase())) { found = i; break; }
            }
            
            if (found >= 0) {
                var optEls = document.querySelectorAll('span.choiceText.rs_preserve > p, label, .option, li');
                if (optEls[found]) { optEls[found].click(); }
                
                submitConfidence();
                clickNext();
                setTimeout(solve, 4000);
            } else {
                document.getElementById('s').innerText = 'No match';
                setTimeout(solve, 2000);
            }
        });
    }
    
    function solveMatching() {
        var qt = getQuestionText();
        var pairs = getMatchingPairs();
        
        document.getElementById('s').innerText = 'Terms: ' + pairs.terms.length + ', Defs: ' + pairs.definitions.length;
        
        if (pairs.terms.length < 2 || pairs.definitions.length < 2) {
            // Try to get more info from page
            var allText = document.body.textContent;
            
            // Parse the matching pairs manually
            // Look for patterns like "Organic Food Production" = definition
            
            // For now, just skip to next question
            document.getElementById('s').innerText = 'Manual required';
            clickNext();
            setTimeout(solve, 3000);
            return;
        }
        
        document.getElementById('s').innerText = 'Matching...';
        
        callAPI('MATCHING QUESTION\n' + qt + '\nTerms (left side): ' + pairs.terms.join(', ') + '\nDescriptions (right side): ' + pairs.definitions.join(' | ') + '\n\nGive the correct matches. Format: Each term = its correct description', function(a) {
            if (a) {
                document.getElementById('s').innerText = 'Got matches: ' + a.substring(0, 30);
            }
            // Matching drag/drop is complex - skip for now
            clickNext();
            setTimeout(solve, 3000);
        });
    }
    
    function solveFillBlank() {
        var qt = getQuestionText();
        var inputs = getFillBlankInputs();
        
        if (!inputs.length) { document.getElementById('s').innerText = 'No inputs'; clickNext(); setTimeout(solve, 2000); return; }
        
        document.getElementById('s').innerText = 'Fill blank...';
        
        callAPI('Fill in the blank: ' + qt + '\nWhat is the correct answer? Just give the answer.', function(a) {
            if (a && inputs[0]) {
                inputs[0].value = a;
                inputs[0].dispatchEvent(new Event('input', {bubbles: true}));
            }
            submitConfidence();
            clickNext();
            setTimeout(solve, 3000);
        });
    }
    
    function solveOrdering() {
        var qt = getQuestionText();
        var opts = getMultipleChoiceOptions();
        
        if (!opts.length) { clickNext(); setTimeout(solve, 2000); return; }
        
        document.getElementById('s').innerText = 'Ordering...';
        
        callAPI('ORDERING: ' + qt + '\nItems: ' + opts.join(', ') + '\nWhat is the correct order?', function(a) {
            document.getElementById('s').innerText = 'Got order';
            clickNext();
            setTimeout(solve, 3000);
        });
    }
    
    function solveTextAnswer(type) {
        var qt = getQuestionText();
        
        document.getElementById('s').innerText = type + '...';
        
        var prompt = (type === 'short answer' ? 'SHORT ANSWER: ' : 'ESSAY: ') + qt + '\nGive a appropriate answer.';
        
        callAPI(prompt, function(a) {
            var inputs = document.querySelectorAll('textarea, input[type="text"]');
            if (a && inputs.length) {
                inputs[0].value = a;
                inputs[0].dispatchEvent(new Event('input', {bubbles: true}));
            }
            submitConfidence();
            clickNext();
            setTimeout(solve, 3000);
        });
    }
    
    function callAPI(prompt, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var a = d.choices[0].message.content.trim();
                callback(a);
            } else {
                callback(null);
            }
        };
        xhr.onerror = function() { callback(null); };
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: prompt }],
            temperature: 0.1
        }));
    }
    
    console.log('QuizGenius loaded! Click Start.');
})();
