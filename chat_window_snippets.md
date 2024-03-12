# AdonAI-Chatbot-Snippets
Code snippets to integrate adon ai as a chatwindow in your js application!

## Embedded

```javascript
document.addEventListener('DOMContentLoaded', function() {
    window.data_whisper_config = {
        user_id: 'TEST_USER',
        api_key: 'TEST_API_KEY',
        display_option: 'embedded'
    };
    var scriptUrl = 'https://nickhawkinstest.z33.web.core.windows.net/bundle.js';
    var cacheBust = '?v=' + Math.random();
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = scriptUrl + cacheBust;
    document.head.appendChild(script);
});
```

## Floating

```javascript
document.addEventListener('DOMContentLoaded', function() {
    window.data_whisper_config = {
        user_id: 'TEST_USER',
        api_key: 'TEST_API_KEY',
        display_option: 'floating'
    };
    var scriptUrl = 'https://nickhawkinstest.z33.web.core.windows.net/bundle.js';
    var cacheBust = '?v=' + Math.random();
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = scriptUrl + cacheBust;
    document.head.appendChild(script);
});
```
