// QuizGenius - McGraw Hill Auto Solver - All Question Types
(function() {
    // Get API key from URL parameter or localStorage
    var params = new URLSearchParams(window.location.search);
    var k = params.get('key') || localStorage.getItem('k');
    
    if (!k) {
        k = prompt('Enter API Key (get free at console.groq.com/keys):');
        if (k) localStorage.setItem('k', k);
    }
    
    if (!k) {
        alert('API key required!');
        return;
    }
    
    // Create panel
    var p = document.createElement('div');
    p.style.cssText = 'position:fixed;top:10px;right:10px;z-index:99999;background:#222;padding:15px;border-radius:10px;color:#fff;font-family:sans-serif;min-width:180px;';
    p.innerHTML = '<b style="color:#0f8">QuizGenius</b><br><span id=s style="font-size:12px">Ready</span><br><button id=st style="background:#0f8;padding:8px 16px;border:none;border-radius:5px;cursor:pointer;margin-top:8px">Start</button>';
    document.body.appendChild(p);
    
    var running = false;
    
    document.getElementById('st').onclick = function() {
        running = true;
        solve();
    };
    
    function getQuestionType() {
        // Check what type of question we're on
        var h1 = document.querySelector('h1');
        var h2 = document.querySelector('h2');
        var text = (h1 ? h1.textContent : '') + (h2 ? h2.textContent : '');
        
        if (text.toLowerCase().includes('matching')) return 'matching';
        if (text.toLowerCase().includes('multiple choice')) return 'multiple_choice';
        if (text.toLowerCase().includes('fill')) return 'fill_blank';
        return 'unknown';
    }
    
    function getMultipleChoice() {
        var opts = [];
        var optEls = document.querySelectorAll('span.choiceText.rs_preserve > p');
        optEls.forEach(function(e) { var t = e.textContent.trim(); if (t) opts.push(t); });
        return { options: opts, elements: optEls };
    }
    
    function getMatching() {
        // Get terms (left side) and descriptions (right side)
        var terms = [];
        var descriptions = [];
        
        // Try to find draggable terms
        document.querySelectorAll('[class*="term"], [class*="draggable"], .term, .match-term').forEach(function(e) {
            var t = e.textContent.trim();
            if (t && t.length < 50) terms.push(t);
        });
        
        // Try to find descriptions/definitions
        document.querySelectorAll('[class*="definition"], [class*="description"], .definition, .desc').forEach(function(e) {
            var t = e.textContent.trim();
            if (t && t.length > 10 && t.length < 200) descriptions.push(t);
        });
        
        // Fallback: get all text content and parse
        if (terms.length === 0) {
            var body = document.body.textContent;
            // Extract terms - usually shorter
            var lines = body.split('\n').filter(function(l) { return l.trim().length > 0; });
            // This is a fallback - user may need to help
        }
        
        return { terms: terms, descriptions: descriptions };
    }
    
    function solve() {
        if (!running) return;
        
        var qType = getQuestionType();
        document.getElementById('s').innerText = 'Type: ' + qType;
        
        if (qType === 'multiple_choice') {
            solveMultipleChoice();
        } else if (qType === 'matching') {
            solveMatching();
        } else {
            document.getElementById('s').innerText = 'Q type: ' + qType;
            setTimeout(solve, 3000);
        }
    }
    
    function solveMultipleChoice() {
        var q = document.querySelector('div.prompt');
        if (!q) { document.getElementById('s').innerText = 'No Q'; setTimeout(solveMultipleChoice, 2000); return; }
        var qt = q.textContent.trim();
        if (qt.length < 5) { setTimeout(solveMultipleChoice, 2000); return; }
        
        var result = getMultipleChoice();
        var opts = result.options;
        var optEls = result.elements;
        
        if (!opts.length) { document.getElementById('s').innerText = 'No opts'; setTimeout(solveMultipleChoice, 2000); return; }
        
        document.getElementById('s').innerText = 'Sending...';
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var a = d.choices[0].message.content.trim();
                document.getElementById('s').innerText = 'Ans: ' + a;
                
                var found = -1;
                for (var i = 0; i < opts.length; i++) {
                    if (a.toLowerCase().includes(opts[i].toLowerCase())) { found = i; break; }
                }
                
                if (found >= 0) {
                    optEls[found].click();
                    document.getElementById('s').innerText = 'Clicked!';
                    
                    setTimeout(function() {
                        // Click confidence
                        var all = document.querySelectorAll('button,span,div');
                        all.forEach(function(b) {
                            var t = b.textContent.trim().toLowerCase();
                            if (t === 'high' || t === 'medium' || t === 'low') b.click();
                        });
                        
                        setTimeout(function() {
                            var btns = document.querySelectorAll('button');
                            btns.forEach(function(b) {
                                if (b.textContent.includes('Next')) b.click();
                            });
                            
                            if (running) setTimeout(solveMultipleChoice, 3000);
                        }, 1500);
                    }, 1000);
                } else {
                    document.getElementById('s').innerText = 'No match';
                    if (running) setTimeout(solveMultipleChoice, 2000);
                }
            } else {
                document.getElementById('s').innerText = 'API err';
                if (running) setTimeout(solveMultipleChoice, 2000);
            }
        };
        xhr.onerror = function() { document.getElementById('s').innerText = 'Net err'; if (running) setTimeout(solveMultipleChoice, 2000); };
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: 'Q: ' + qt + ' Options: ' + opts.join(' | ') + ' Just say the option text.' }],
            temperature: 0.1
        }));
    }
    
    function solveMatching() {
        var result = getMatching();
        
        if (result.terms.length === 0 || result.descriptions.length === 0) {
            document.getElementById('s').innerText = 'Matching: need manual';
            // Try to click skip/next for now
            setTimeout(function() {
                var btns = document.querySelectorAll('button');
                btns.forEach(function(b) {
                    if (b.textContent.includes('Next')) b.click();
                });
                if (running) setTimeout(solveMatching, 3000);
            }, 2000);
            return;
        }
        
        document.getElementById('s').innerText = 'Solving matching...';
        
        var qt = 'Match these terms: ' + result.terms.join(', ');
        var opts = result.descriptions;
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'https://api.groq.com/openai/v1/chat/completions', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', 'Bearer ' + k);
        xhr.onload = function() {
            if (xhr.status === 200) {
                var d = JSON.parse(xhr.responseText);
                var a = d.choices[0].message.content.trim();
                document.getElementById('s').innerText = 'Ans: ' + a.substring(0, 50);
                
                // Matching is complex - just skip for now
                setTimeout(function() {
                    var btns = document.querySelectorAll('button');
                    btns.forEach(function(b) {
                        if (b.textContent.includes('Next')) b.click();
                    });
                    if (running) setTimeout(solveMatching, 3000);
                }, 2000);
            }
        };
        xhr.onerror = function() { document.getElementById('s').innerText = 'Err'; if (running) setTimeout(solveMatching, 2000); };
        xhr.send(JSON.stringify({
            model: 'llama-3.1-8b-instant',
            messages: [{ role: 'user', content: qt + ' | Descriptions: ' + opts.join(' | ') + ' Give matches in format: term = description' }],
            temperature: 0.1
        }));
    }
    
    console.log('QuizGenius loaded! Click Start.');
})();
