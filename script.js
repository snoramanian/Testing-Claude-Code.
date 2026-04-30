(function () {
  const form = document.getElementById('login-form');
  const message = document.getElementById('message');

  const SESSION_KEY = 'demo.session';

  function setMessage(text, kind) {
    message.textContent = text;
    message.classList.remove('error', 'success');
    if (kind) message.classList.add(kind);
  }

  function authenticate(username, password) {
    const users = window.DEMO_USERS || [];
    return users.find(u => u.username === username && u.password === password) || null;
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !password) {
      setMessage('Please enter both username and password.', 'error');
      return;
    }

    const user = authenticate(username, password);
    if (!user) {
      setMessage('Invalid username or password.', 'error');
      return;
    }

    const session = { username: user.username, loggedInAt: new Date().toISOString() };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    setMessage('Login successful. Redirecting...', 'success');
    setTimeout(() => { window.location.href = 'welcome.html'; }, 600);
  });

  if (sessionStorage.getItem(SESSION_KEY)) {
    setMessage('You are already signed in.', 'success');
  }
})();
