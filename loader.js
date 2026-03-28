// Minimal loader - loads main script
var s = document.createElement('script');
s.src = '//quizgenius-nji8.onrender.com/quizgenius.js';
s.onload = function() { console.log('QuizGenius loaded! Click Start.'); };
s.onerror = function() { alert('Failed to load. Try console version.'); };
document.head.appendChild(s);
