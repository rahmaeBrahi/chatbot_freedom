const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const chatMessages = document.getElementById('chat-messages');
const sendBtn = document.getElementById('send-btn');
const calendarPicker = document.getElementById('calendar-picker');
const calendarGrid = document.getElementById('calendar-grid');
const slotsGrid = document.getElementById('slots-grid');
const calMonthLabel = document.getElementById('cal-month-label');
const quickRepliesContainer = document.getElementById('quick-replies');
const confirmWrap = document.getElementById('confirm-slot-wrap');
const confirmBtn = document.getElementById('confirm-slot-btn');

let sessionId = localStorage.getItem('session_id') || null;
let chatHistory = [];

// Calendar state
let calCurrentDate = new Date();
let calSelectedDate = null;   // JS Date
let calSelectedTime = null;   // string e.g. "9:00 AM"

const ALL_SLOTS = ['9:00 AM','10:00 AM','11:00 AM','12:00 PM','1:00 PM','2:00 PM','3:00 PM','4:00 PM','5:00 PM'];
const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

/* ── Utilities ── */
function toYMD(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

/* ── Calendar rendering ── */
function renderCalendar() {
    const year = calCurrentDate.getFullYear();
    const month = calCurrentDate.getMonth();
    calMonthLabel.textContent = `${MONTHS[month]} ${year}`;

    calendarGrid.innerHTML = '';

    // Day headers
    DAYS.forEach(d => {
        const el = document.createElement('div');
        el.className = 'cal-day-label';
        el.textContent = d;
        calendarGrid.appendChild(el);
    });

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date(); today.setHours(0,0,0,0);

    // Empty cells
    for (let i = 0; i < firstDay; i++) {
        const el = document.createElement('div');
        el.className = 'cal-day cal-empty';
        calendarGrid.appendChild(el);
    }

    for (let d = 1; d <= daysInMonth; d++) {
        const date = new Date(year, month, d);
        const dayOfWeek = date.getDay();
        const isPast = date < today;
        const isSunday = dayOfWeek === 0;
        const isToday = toYMD(date) === toYMD(today);
        const isSelected = calSelectedDate && toYMD(date) === toYMD(calSelectedDate);

        const el = document.createElement('div');
        el.className = 'cal-day';
        if (isPast || isSunday) el.classList.add('cal-disabled');
        if (isToday) el.classList.add('cal-today');
        if (isSelected) el.classList.add('cal-selected');
        el.textContent = d;

        if (!isPast && !isSunday) {
            el.addEventListener('click', () => selectDate(date));
        }
        calendarGrid.appendChild(el);
    }
}

async function selectDate(date) {
    calSelectedDate = date;
    calSelectedTime = null;
    renderCalendar();
    await loadSlots(toYMD(date));
}

async function loadSlots(dateStr) {
    slotsGrid.innerHTML = '<div class="slot-loading">Loading available slots…</div>';
    document.getElementById('time-slots').style.display = 'block';

    let bookedSlots = [];
    try {
        const resp = await fetch(`/slots?date=${dateStr}`);
        if (resp.ok) {
            const data = await resp.json();
            bookedSlots = (data.booked_slots || []).map(s => s.trim().toLowerCase());
        }
    } catch (_) {}

    slotsGrid.innerHTML = '';
    ALL_SLOTS.forEach(slot => {
        const isBooked = bookedSlots.includes(slot.toLowerCase());
        const btn = document.createElement('button');
        btn.className = 'slot-btn' + (isBooked ? ' slot-booked' : '');
        btn.textContent = slot;
        btn.disabled = isBooked;
        btn.addEventListener('click', () => selectSlot(slot, btn));
        slotsGrid.appendChild(btn);
    });
}

function selectSlot(slot, btn) {
    // Deselect previous
    slotsGrid.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('slot-selected'));
    btn.classList.add('slot-selected');
    calSelectedTime = slot;
    // Show confirm button
    confirmWrap.classList.remove('hidden');
}

/* ── Show/hide calendar ── */
function showCalendar() {
    calCurrentDate = new Date();
    calSelectedDate = null;
    calSelectedTime = null;
    confirmWrap.classList.add('hidden');
    document.getElementById('time-slots').style.display = 'none';
    renderCalendar();
    calendarPicker.classList.remove('hidden');
}

function hideCalendar() {
    calendarPicker.classList.add('hidden');
}

document.getElementById('cal-prev').addEventListener('click', () => {
    calCurrentDate.setMonth(calCurrentDate.getMonth() - 1);
    renderCalendar();
});
document.getElementById('cal-next').addEventListener('click', () => {
    calCurrentDate.setMonth(calCurrentDate.getMonth() + 1);
    renderCalendar();
});

// Confirm button: auto-submit without typing
confirmBtn.addEventListener('click', async () => {
    if (!calSelectedDate || !calSelectedTime) return;
    const dateLabel = calSelectedDate.toLocaleDateString('en-IE', { weekday:'long', day:'numeric', month:'long' });
    const displayMsg = `📅 ${dateLabel} at ${calSelectedTime}`;
    appendMessage('user', displayMsg);
    clearQuickReplies();
    hideCalendar();
    showTypingIndicator();
    // Build internal message with date/time tags for the AI
    const internalMsg = `I'd like to book an appointment.\n[appointment_date: ${toYMD(calSelectedDate)}]\n[preferred_time: ${calSelectedTime}]`;
    await sendMessageRaw(internalMsg);
});

/* ── Chat core ── */
function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', role === 'user' ? 'user-message' : 'bot-message');
    const formattedContent = content.replace(/\n/g, '<br>');
    msgDiv.innerHTML = `<div class="message-content">${formattedContent}</div>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    if (role === 'user') clearQuickReplies();
}

function renderQuickReplies(buttons) {
    clearQuickReplies();
    if (!buttons || buttons.length === 0) return;
    buttons.forEach(buttonText => {
        const btn = document.createElement('button');
        btn.classList.add('quick-reply-btn');
        btn.textContent = buttonText;
        btn.onclick = () => handleButtonClick(buttonText);
        quickRepliesContainer.appendChild(btn);
    });
}

function clearQuickReplies() { quickRepliesContainer.innerHTML = ''; }

async function handleButtonClick(text) {
    if (text.toLowerCase().includes('book appointment')) {
        showCalendar();
        appendMessage('user', text);
        clearQuickReplies();
        showTypingIndicator();
        await sendMessageToServer(text);
        return;
    }
    appendMessage('user', text);
    clearQuickReplies();
    showTypingIndicator();
    await sendMessageToServer(text);
}

async function sendMessageRaw(message) {
    await sendMessageToServer(message);
}

async function sendMessage(message) {
    let fullMessage = message;
    if (!calendarPicker.classList.contains('hidden')) {
        if (calSelectedDate && calSelectedTime) {
            hideCalendar();
            fullMessage = `${message}\n[appointment_date: ${toYMD(calSelectedDate)}]\n[preferred_time: ${calSelectedTime}]`;
        } else {
            hideCalendar();
        }
    }
    await sendMessageToServer(fullMessage);
}

async function sendMessageToServer(fullMessage) {
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: fullMessage,
                session_id: sessionId,
                history: chatHistory
            })
        });

        const data = await response.json();
        removeTypingIndicator();

        if (data.output) {
            appendMessage('bot', data.output);
            chatHistory.push({ role: 'user', content: fullMessage });
            chatHistory.push({ role: 'bot', content: data.output });
            if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
            if (data.buttons) renderQuickReplies(data.buttons);
            if (data.session_id) {
                sessionId = data.session_id;
                localStorage.setItem('session_id', sessionId);
            }
        } else if (data.error) {
            appendMessage('bot', "I'm sorry, I encountered an error. Please try again later.");
            console.error(data.error);
        }
    } catch (error) {
        removeTypingIndicator();
        appendMessage('bot', "Connection error. Is the server running?");
        console.error(error);
    }
}

function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.classList.add('message', 'bot-message', 'typing-indicator');
    indicator.id = 'typing-indicator';
    indicator.innerHTML = '<div class="message-content">Freedom Dental Assistant is typing…</div>';
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;
    appendMessage('user', message);
    userInput.value = '';
    showTypingIndicator();
    await sendMessage(message);
});

window.onload = () => {
    renderQuickReplies([
        "Book Appointment",
        "Dental Implants",
        "Teeth Whitening",
        "General Cleaning",
        "Ask a Question"
    ]);
};
