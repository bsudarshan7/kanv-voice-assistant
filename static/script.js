const micButton = document.getElementById('micButton');
const voiceStage = document.querySelector('.voice-stage');
const listeningLabel = document.getElementById('listeningLabel');
const statusText = document.getElementById('statusText');
const browserNote = document.getElementById('browserNote');
const commandForm = document.getElementById('commandForm');
const commandInput = document.getElementById('commandInput');
const responseText = document.getElementById('responseText');
const responseTime = document.getElementById('responseTime');
const actionLink = document.getElementById('actionLink');
const soundWave = document.getElementById('soundWave');

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

function setStatus(label, state = '') {
  statusText.textContent = label;
  voiceStage.classList.toggle('listening', state === 'listening');
  voiceStage.classList.toggle('busy', state === 'busy');
}

function showReply(reply, actionUrl = '', actionLabel = '') {
  responseText.textContent = reply;
  responseTime.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if (actionUrl) {
    actionLink.href = actionUrl;
    actionLink.textContent = `${actionLabel || 'Open result'} ↗`;
    actionLink.hidden = false;
  } else {
    actionLink.hidden = true;
    actionLink.removeAttribute('href');
  }
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(reply);
    utterance.lang = 'en-IN';
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  }
}

async function sendCommand(command) {
  const cleaned = command.trim();
  if (!cleaned) return;
  commandInput.value = cleaned;
  actionLink.hidden = true;
  setStatus('THINKING', 'busy');
  listeningLabel.textContent = `PROCESSING: “${cleaned.slice(0, 55)}${cleaned.length > 55 ? '…' : ''}”`;
  try {
    const response = await fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cleaned })
    });
    const data = await response.json();
    showReply(data.reply || 'I could not process that command.', data.action_url || '', data.action_label || 'Open result');
    setStatus('SYSTEM READY');
    listeningLabel.textContent = 'TAP THE MIC TO START SPEAKING';
  } catch (error) {
    showReply('I could not reach the Flask server. Make sure app.py is running in your terminal and refresh this page.');
    setStatus('CONNECTION ERROR');
    listeningLabel.textContent = 'CHECK THE FLASK SERVER';
  }
}

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = 'en-IN';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => {
    isListening = true;
    micButton.setAttribute('aria-label', 'Stop voice input');
    setStatus('LISTENING', 'listening');
    listeningLabel.textContent = 'I’M LISTENING… SPEAK NOW';
  };
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    commandInput.value = transcript;
    sendCommand(transcript);
  };
  recognition.onerror = (event) => {
    const messages = {
      'not-allowed': 'Microphone permission was denied. Allow microphone access in your browser, or type a command.',
      'no-speech': 'I did not hear anything. Please try again, or type a command.',
      'network': 'Browser speech recognition needs a network connection. You can type a command instead.'
    };
    showReply(messages[event.error] || `Voice input failed (${event.error}). Please type a command instead.`);
    listeningLabel.textContent = 'VOICE INPUT NOT ACTIVE';
    setStatus('VOICE INPUT ISSUE');
  };
  recognition.onend = () => {
    isListening = false;
    micButton.setAttribute('aria-label', 'Start voice input');
    if (statusText.textContent === 'LISTENING') {
      setStatus('SYSTEM READY');
      listeningLabel.textContent = 'TAP THE MIC TO START SPEAKING';
    }
  };
} else {
  micButton.disabled = true;
  micButton.style.opacity = '.45';
  browserNote.textContent = 'This browser does not support Web Speech API voice input. Use Chrome or Microsoft Edge, or type a command below.';
  listeningLabel.textContent = 'VOICE INPUT NOT SUPPORTED IN THIS BROWSER';
}

micButton.addEventListener('click', () => {
  if (!recognition) return;
  try {
    if (isListening) recognition.stop();
    else recognition.start();
  } catch (error) {
    showReply('Voice input could not start. If it is already listening, wait a moment and try again.');
  }
});

commandForm.addEventListener('submit', (event) => {
  event.preventDefault();
  sendCommand(commandInput.value);
});

document.querySelectorAll('.command-chip').forEach((button) => {
  button.addEventListener('click', () => sendCommand(button.dataset.command || ''));
});


// Read-only monitoring dashboard. Results are rendered as text, never as HTML.
const devopsResult = document.getElementById('devopsResult');
function renderDevopsResult(message, isError = false) {
  if (!devopsResult) return;
  devopsResult.classList.toggle('error', isError);
  devopsResult.replaceChildren();
  const dot = document.createElement('span');
  dot.className = 'devops-result-dot';
  const content = document.createElement('span');
  content.textContent = message;
  devopsResult.append(dot, content);
}

async function runDevopsAction(action) {
  const labels = { health: 'Checking KANV health…', docker: 'Checking Docker containers…', aws: 'Querying AWS EC2 instances…' };
  renderDevopsResult(labels[action] || 'Checking…');
  const endpoint = {
    health: '/api/devops/health',
    docker: '/api/devops/docker/containers',
    aws: '/api/devops/aws/instances'
  }[action];
  if (!endpoint) return;
  try {
    const response = await fetch(endpoint, { headers: { 'Accept': 'application/json' } });
    const data = await response.json();
    if (!response.ok || data.ok === false) {
      renderDevopsResult(data.message || 'The check failed. See the setup notes in README.md.', true);
      showReply(data.message || 'The monitoring check failed.');
      return;
    }
    let message = '';
    if (action === 'health') {
      message = `KANV is ${data.status}. Checked at ${new Date(data.checked_at).toLocaleTimeString()}.`;
    } else if (action === 'docker') {
      const items = data.containers || [];
      message = items.length ? `Docker: ${items.length} container(s). ` + items.slice(0, 10).map(item => `${item.name} — ${item.status} — ${item.image}`).join(' | ') : 'Docker is connected; no containers were found.';
    } else {
      const items = data.instances || [];
      message = items.length ? `AWS region ${data.region}: ${items.length} EC2 instance(s). ` + items.slice(0, 10).map(item => `${item.name} (${item.instance_id}) — ${item.state} — ${item.instance_type} — ${item.availability_zone}`).join(' | ') : `Connected to AWS region ${data.region}; no EC2 instances were found there.`;
    }
    renderDevopsResult(message);
    showReply(message);
  } catch (error) {
    const message = 'Could not reach the KANV Flask server. Confirm app.py is running and refresh the page.';
    renderDevopsResult(message, true);
    showReply(message);
  }
}

document.querySelectorAll('[data-devops]').forEach((button) => {
  button.addEventListener('click', () => runDevopsAction(button.dataset.devops));
});
