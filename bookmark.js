// QuizGenius - McGraw Hill Auto Solver
try {
var k = localStorage.getItem('k');
if (!k || k === 'null') {
    k = prompt('API Key (get free at console.groq.com/keys):');
    if (k) localStorage.setItem('k', k);
}
if (!k) { throw new Error('No API key'); }

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

function solve() {
    if (!running) return;
    
    var q = document.querySelector('div.prompt');
    if (!q) { document.getElementById('s').innerText = 'No Q'; setTimeout(solve, 2000); return; }
    var qt = q.textContent.trim();
    if (qt.length < 5) { setTimeout(solve, 2000); return; }
    
    var opts = [];
    var optEls = document.querySelectorAll('span.choiceText.rs_preserve > p');
    optEls.forEach(function(e) { var t = e.textContent.trim(); if (t) opts.push(t); });
    if (!opts.length) { document.getElementById('s').innerText = 'No opts'; setTimeout(solve, 2000); return; }
    
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
                        // Click Next
                        var btns = document.querySelectorAll('button');
                        btns.forEach(function(b) {
                            if (b.textContent.includes('Next')) b.click();
                        });
                        
                        if (running) setTimeout(solve, 3000);
                    }, 1500);
                }, 1000);
            } else {
                document.getElementById('s').innerText = 'No match';
                if (running) setTimeout(solve, 2000);
            }
        } else {
            document.getElementById('s').innerText = 'API err';
            if (running) setTimeout(solve, 2000);
        }
    };
    xhr.onerror = function() { document.getElementById('s').innerText = 'Net err'; if (running) setTimeout(solve, 2000); };
    xhr.send(JSON.stringify({
        model: 'llama-3.1-8b-instant',
        messages: [{ role: 'user', content: 'Q: ' + qt + ' Options: ' + opts.join(' | ') + ' Just say the option text.' }],
        temperature: 0.1
    }));
}

console.log('QuizGenius loaded! Click Start.');
} catch(e) { console.error(e); alert(e.message); }
