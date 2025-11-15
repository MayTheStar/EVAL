// Chatbot JavaScript

let isProcessing = false;

document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const chatWelcome = document.getElementById('chat-welcome');

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = chatInput.scrollHeight + 'px';
    });

    // Send on Enter (Shift+Enter for new line)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Send button click
    sendButton.addEventListener('click', sendMessage);
});

async function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const query = chatInput.value.trim();

    if (!query || isProcessing) return;

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Hide welcome message
    const chatWelcome = document.getElementById('chat-welcome');
    if (chatWelcome) {
        chatWelcome.style.display = 'none';
    }

    // Add user message
    addMessage('user', query);

    // Show typing indicator
    const typingId = addMessage('bot', '<div class="typing-indicator">Thinking</div>', true);

    isProcessing = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });

        const data = await response.json();

        // Remove typing indicator
        const typingElement = document.getElementById(typingId);
        if (typingElement) {
            typingElement.remove();
        }

        if (data.success) {
            // Add bot response
            addMessage('bot', formatBotResponse(data.answer, data.sources));
        } else {
            addMessage('bot', `Error: ${data.message}`);
        }

    } catch (error) {
        // Remove typing indicator
        const typingElement = document.getElementById(typingId);
        if (typingElement) {
            typingElement.remove();
        }

        addMessage('bot', `Error: ${error.message}`);
    } finally {
        isProcessing = false;
    }
}

function addMessage(sender, content, isTemporary = false) {
    const chatMessages = document.getElementById('chat-messages');
    const messageId = 'msg-' + Date.now();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    if (isTemporary) {
        messageDiv.id = messageId;
    }

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = sender === 'user' ? '👤' : '🤖';

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    if (typeof content === 'string') {
        messageContent.innerHTML = content;
    } else {
        messageContent.appendChild(content);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);

    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

function formatBotResponse(answer, sources) {
    const container = document.createElement('div');
    container.className = 'bot-response-container';

    // --- Format text ---
    const answerDiv = document.createElement('div');
    answerDiv.className = 'message-text';

    // Convert Markdown-like formatting into HTML
    let formatted = answer
        .replace(/^\[/, '')                               // remove starting bracket
        .replace(/\]$/, '')                               // remove ending bracket
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // bold
        .replace(/^####\s?(.*)$/gm, '<h4>$1</h4>')         // #### headings
        .replace(/^###\s?(.*)$/gm, '<h3>$1</h3>')          // ### headings
        .replace(/^##\s?(.*)$/gm, '<h2>$1</h2>')           // ## headings
        .replace(/^#\s?(.*)$/gm, '<h1>$1</h1>')            // # headings
        .replace(/\n\n/g, '</p><p>')                       // paragraph breaks
        .replace(/\n/g, '<br>')                            // single line break
        .replace(/(\d+)\.\s/g, '<br><strong>$1.</strong> '); // numbered points

    formatted = `<p>${formatted}</p>`;


    answerDiv.innerHTML = formatted;
    container.appendChild(answerDiv);

    // --- 📚 Sources (restored to original style) ---
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';

        // Title same as original
        const sourcesTitle = document.createElement('div');
        sourcesTitle.className = 'sources-title';
        sourcesTitle.textContent = '📚 Sources:';
        sourcesDiv.appendChild(sourcesTitle);

        // Source items same structure and tone as before
        sources.forEach((source, index) => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';

            let sourceText = `${index + 1}. ${source.label || 'Unnamed Source'}`;
            if (source.page) {
                sourceText += ` (Page ${source.page})`;
            }
            if (source.distance !== undefined) {
                sourceText += ` - Distance: ${source.distance.toFixed(4)}`;
            }

            sourceItem.textContent = sourceText;
            sourcesDiv.appendChild(sourceItem);
        });

        container.appendChild(sourcesDiv);
    }

    return container;
}


// Add CSS for typing indicator
const style = document.createElement('style');
style.textContent = `
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #666;
    }
    
    .typing-indicator::after {
        content: '...';
        animation: typing 1.5s infinite;
    }
    
    @keyframes typing {
        0%, 20% { content: '.'; }
        40%, 60% { content: '..'; }
        80%, 100% { content: '...'; }
    }
`;
document.head.appendChild(style);