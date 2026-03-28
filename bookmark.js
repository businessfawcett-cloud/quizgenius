// QuizGenius - McGraw Hill Auto Solver
var k = localStorage.getItem('k');
if (!k) {
    k = prompt('API Key:');
    if (!k) {
        alert('Get key at console.groq.com/keys');
    } else {
        localStorage.setItem('k', k);
    }
}

if (k) {
    // Create panel
    var p = document.createElement('div');
    p.style = 'position:fixed;top:10px;right:10px;z-index:99999;background:#111;padding:12px;border-radius:8px;color:#fff;font-family:sans-serif;width:220px;';
    p.innerHTML = '<b style="color:#00d4aa;">QuizGenius</b><br><span id="s" style="font-size:11px;color:#888;">Ready</span><br><button id="startBtn">Start</button>';
    document.body.appendChild(p);
    
    var r = false;
    
    document.getElementById('startBtn').addEventListener('click', function() {
        r = true;
        solve();
    });
    
    function getAns(t, o) {
        t = t.toLowerCase();
        for (var i = 0; i < o.length; i++) {
            if (t.includes(o[i].toLowerCase())) {
                return i;
            }
        }
        return -1;
    }
    
    function solve() {
        if (!r) return;
        
        var q = document.querySelector('div.prompt');
        var qt = q ? q.textContent.trim() : '';
        
        if (qt.length < 5) {
            document.getElementById('s').innerText = 'No Q';
            if (r) setTimeout(solve, 2000);
            return;
        }
        
        var opts = [];
        var optEls = document.querySelectorAll('span.choiceText.rs_preserve > p');
        optEls.forEach(function(e) {
            var t = e.textContent.trim();
            if (t.length > 0) opts.push(t);
        });
        
        if (opts.length === 0) {
            document.getElementById('s').innerText = 'No opts';
            if (r) setTimeout(solve, 2000);
            return;
        }
        
        document.getElementById('s').innerText = 'Sending...';
        
        fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + k,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'llama-3.1-8b-instant',
                messages: [{
                    role: 'user',
                    content: 'Q: ' + qt + ' Options: ' + opts.join(' | ') + ' Just say the option text.'
                }],
                temperature: 0.1
            })
        }).then(function(x) {
            return x.json();
        }).then(function(d) {
            var a = d.choices[0].message.content.trim();
            document.getElementById('s').innerText = 'AI: ' + a;
            
            var idx = getAns(a, opts);
            
            if (idx >= 0) {
                var el = optEls[idx];
                if (el) {
                    el.click();
                    document.getElementById('s').innerText = 'Clicked!';
                    
                    // Click confidence button
                    setTimeout(function() {
                        var confBtns = document.querySelectorAll('button, span, div');
                        confBtns.forEach(function(b) {
                            var t = b.textContent.trim().toLowerCase();
                            if (t === 'high' || t === 'medium' || t === 'low') {
                                b.click();
                                document.getElementById('s').innerText = 'Conf: ' + t;
                            }
                        });
                        
                        // Click Next
                        setTimeout(function() {
                            var btns = document.querySelectorAll('button');
                            btns.forEach(function(b) {
                                if (b.textContent.includes('Next')) {
                                    b.click();
                                    document.getElementById('s').innerText = 'Next!';
                                }
                            });
                            
                            if (r) setTimeout(solve, 3000);
                        }, 1500);
                    }, 1000);
                    return;
                }
            }
            
            document.getElementById('s').innerText = 'No match';
            if (r) setTimeout(solve, 2000);
        }).catch(function(e) {
            document.getElementById('s').innerText = 'Err';
            if (r) setTimeout(solve, 2000);
        });
    }
    
    console.log('QuizGenius loaded! Click Start.');
}
