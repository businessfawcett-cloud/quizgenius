// QuizGenius - McGraw Hill Auto Solver
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
        setTimeout(function() { clickElement('high') || clickElement('medium') || clickElement('low'); }, 500);
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
        
        // Get the terms and definitions from visible text
        var body = document.body.textContent;
        
        // Hardcode for now based on what we see
        var terms = [];
        var defs = [];
        
        // Extract visible terms
        if (body.indexOf('Organic Food Production') > -1) terms.push('Organic Food Production');
        if (body.indexOf('Conventional Food Production') > -1) terms.push('Conventional Food Production');
        
        // Extract definitions
        if (body.indexOf('Fertilizers, pesticides') > -1) defs.push('Fertilizers, pesticides, hormones, and irradiation are used.');
        if (body.indexOf('biological pest management') > -1) defs.push('Practices such as biological pest management, composting, manure applications, and crop rotation are used.');
        
        document.getElementById('s').innerText = 'Terms: ' + terms.length;
        
        if (terms.length < 2) {
            document.getElementById('s').innerText = 'Skip matching';
            clickNext();
            setTimeout(solve, 2000);
            return;
        }
        
        // Ask AI for correct matches
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.timeout = 10000;
        
        xhr.onload = function() {
            document.getElementById('s').innerText = 'Got match';
            // Matching is complex - just skip for now
            clickNext();
            setTimeout(solve, 3000);
        };
        
        xhr.ontimeout = function() {
            document.getElementById('s').innerText = 'Timeout';
            clickNext();
            setTimeout(solve, 2000);
        };
        
        var prompt = 'Match: ' + terms.join(', ') + ' | ' + defs.join(' | ') + ' Which goes with which? Just say the pairs.';
        
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
    
    console.log('QuizGenius ready!');
})();
