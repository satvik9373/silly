using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace Atticus;

static class WebRuntimeSelfTest
{
    public static int Run()
    {
        using var context = new Context();
        Application.Run(context);
        return context.Result;
    }

    sealed class Context : ApplicationContext
    {
        readonly Form host = new() { ShowInTaskbar = false, WindowState = FormWindowState.Minimized };
        WebView2 web;
        readonly List<JsonElement> messages = new();
        public int Result { get; private set; } = 1;

        public Context() => Start();

        async void Start()
        {
            try
            {
                host.Show();
                web = await Web.Load(host, "settings.html", (_, body) => messages.Add(body), false,
                    "window.__sillyWebErrors=[]; addEventListener('error',e=>__sillyWebErrors.push(String(e.message||e.error||e))); addEventListener('unhandledrejection',e=>__sillyWebErrors.push(String(e.reason||e)));");
                web.CoreWebView2.NavigationCompleted += NavigationCompleted;
            }
            catch (Exception e)
            {
                Console.Error.WriteLine($"web selftest setup failed: {e.Message}");
                Exit();
            }
        }

        async void NavigationCompleted(object sender, CoreWebView2NavigationCompletedEventArgs e)
        {
            if (!e.IsSuccess)
            {
                Console.Error.WriteLine($"web selftest navigation failed: {e.WebErrorStatus}");
                Exit();
                return;
            }
            await Task.Delay(1000);
            await web.CoreWebView2.ExecuteScriptAsync("""
                (() => {
                  if (!customElements.get('wa-select') || !customElements.get('wa-option')) {
                    return {
                      baseURI: document.baseURI,
                      scripts: [...document.scripts].map(s => s.src).filter(Boolean),
                      css: [...document.styleSheets].map(s => s.href).filter(Boolean),
                      registeredSelect: !!customElements.get('wa-select'),
                      registeredOption: !!customElements.get('wa-option'),
                      modelOptions: [],
                      voiceOptions: [],
                      modelValue: '',
                      modelLabel: '',
                      errors: window.__sillyWebErrors.concat('Web Awesome custom elements were not registered')
                    };
                  }
                  window.st.load({
                    prefs: {
                      talkMode:'hold', input:'voice', hotkeyLabel:'Ctrl+Alt+Space', volume:.3, aheadDelay:.9, ahead:true,
                      model:'haiku', aiPrimary:'claude-code', aiBackup1:'none', gnaniLanguage:'en-IN',
                      gnaniVocabularyStrength:'1.0', gnaniTtsModel:'timbre-v3.0', gnaniTtsVoice:'Shivani',
                      gnaniTtsLanguage:'en-IN', gnaniTtsSpeed:1, soundStart:'None', soundDone:'None', soundStop:'None'
                    },
                    sounds:[{value:'None',label:'No sound'}],
                    options:{
                      speechLanguages:[{value:'en-IN',label:'English (India)'},{value:'hi-IN',label:'Hindi'}],
                      ttsModels:[{value:'timbre-v3.0',label:'Timbre v3.0'},{value:'timbre-v2.5',label:'Timbre v2.5'}],
                      ttsLanguages:[{value:'en-IN',label:'en-IN'},{value:'auto',label:'auto'}],
                      vocabularyStrengths:[{value:'0.5',label:'0.5'},{value:'1.0',label:'1.0'}],
                      aiPrimary:[{value:'claude-code',label:'Claude subscription'},{value:'openai',label:'ChatGPT plan'}],
                      aiBackup:[{value:'none',label:'No backup'},{value:'openai',label:'ChatGPT plan'}]
                    },
                    ttsCatalog:{
                      'timbre-v3.0':[{value:'Shivani',label:'Shivani'},{value:'Lakshmi',label:'Lakshmi'}],
                      'timbre-v2.5':[{value:'Kaveri',label:'Kaveri'},{value:'Poorvi',label:'Poorvi'}]
                    }
                  });
                  const select = key => document.querySelector(`[data-option-key="${key}"]`);
                  const voice = document.querySelector('[data-k="gnaniTtsVoice"]');
                  const model = select('ttsModels');
                  const display = el => el.shadowRoot?.querySelector('.display-input')?.value || '';
                  const displayColor = el => el.shadowRoot ? getComputedStyle(el.shadowRoot.querySelector('.display-input')).color : '';
                  const optionColor = el => getComputedStyle(el).color;
                  return {
                    baseURI: document.baseURI,
                    scripts: [...document.scripts].map(s => s.src).filter(Boolean),
                    css: [...document.styleSheets].map(s => s.href).filter(Boolean),
                    registeredSelect: !!customElements.get('wa-select'),
                    registeredOption: !!customElements.get('wa-option'),
                    modelOptions: [...model.querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    voiceOptions: [...voice.querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    modelValue: model.value,
                    modelLabel: display(model),
                    displayColor: displayColor(model),
                    optionColors: [...model.querySelectorAll('wa-option')].map(optionColor),
                    errors: window.__sillyWebErrors
                  };
                })()
                """);
            await Task.Delay(300);
            await web.CoreWebView2.ExecuteScriptAsync("""
                (() => {
                  const model = document.querySelector('[data-option-key="ttsModels"]');
                  model.value = 'timbre-v2.5';
                  model.dispatchEvent(new Event('change', { bubbles: true }));
                  return true;
                })()
                """);
            await Task.Delay(300);
            var result = await web.CoreWebView2.ExecuteScriptAsync("""
                (() => {
                  const select = key => document.querySelector(`[data-option-key="${key}"]`);
                  const model = select('ttsModels');
                  const voice = document.querySelector('[data-k="gnaniTtsVoice"]');
                  const display = el => el.shadowRoot?.querySelector('.display-input')?.value || '';
                  const displayColor = el => el.shadowRoot ? getComputedStyle(el.shadowRoot.querySelector('.display-input')).color : '';
                  const optionColor = el => getComputedStyle(el).color;
                  return {
                    baseURI: document.baseURI,
                    scripts: [...document.scripts].map(s => s.src).filter(Boolean),
                    css: [...document.styleSheets].map(s => s.href).filter(Boolean),
                    registeredSelect: !!customElements.get('wa-select'),
                    registeredOption: !!customElements.get('wa-option'),
                    modelOptions: [...model.querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    voiceOptions: [...voice.querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    speechLanguageOptions: [...select('speechLanguages').querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    ttsLanguageOptions: [...select('ttsLanguages').querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    vocabularyOptions: [...select('vocabularyStrengths').querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    primaryOptions: [...select('aiPrimary').querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    backupOptions: [...select('aiBackup').querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    soundOptions: [...document.querySelector('[data-k="soundStart"]').querySelectorAll('wa-option')].map(o => ({value:o.value,label:o.textContent})),
                    modelValue: model.value,
                    modelLabel: display(model),
                    displayColor: displayColor(model),
                    optionColors: [...model.querySelectorAll('wa-option')].map(optionColor),
                    errors: window.__sillyWebErrors
                  };
                })()
                """);
            await web.CoreWebView2.ExecuteScriptAsync("""
                st.load({prefs:{gnaniTtsModel:'timbre-v2.5',gnaniTtsVoice:'Kaveri'}});
                """);
            await Task.Delay(300);
            var restored = await web.CoreWebView2.ExecuteScriptAsync("""
                (() => {
                  const model = document.querySelector('[data-option-key="ttsModels"]');
                  const voice = document.querySelector('[data-k="gnaniTtsVoice"]');
                  return { model: model.value, voice: voice.value };
                })()
                """);
            Console.WriteLine(result);
            Console.WriteLine($"RESTORED={restored}");
            try
            {
                using var data = JsonDocument.Parse(result);
                using var restoredData = JsonDocument.Parse(restored);
                var root = data.RootElement;
                var restoredRoot = restoredData.RootElement;
                var savedModel = messages.Any(message =>
                    message.TryGetProperty("do", out var action) && action.GetString() == "set" &&
                    message.TryGetProperty("k", out var key) && key.GetString() == "gnaniTtsModel" &&
                    message.TryGetProperty("v", out var value) && value.GetString() == "timbre-v2.5");
                var ok = root.GetProperty("registeredSelect").GetBoolean()
                    && root.GetProperty("registeredOption").GetBoolean()
                    && root.GetProperty("modelOptions").GetArrayLength() == 2
                    && root.GetProperty("voiceOptions").GetArrayLength() == 2
                    && root.GetProperty("speechLanguageOptions").GetArrayLength() == 2
                    && root.GetProperty("ttsLanguageOptions").GetArrayLength() == 2
                    && root.GetProperty("vocabularyOptions").GetArrayLength() == 2
                    && root.GetProperty("primaryOptions").GetArrayLength() == 2
                    && root.GetProperty("backupOptions").GetArrayLength() == 2
                    && root.GetProperty("soundOptions").GetArrayLength() == 1
                    && root.GetProperty("modelValue").GetString() == "timbre-v2.5"
                    && root.GetProperty("modelLabel").GetString() == "Timbre v2.5"
                    && root.GetProperty("displayColor").GetString() != "rgb(29, 29, 31)"
                    && root.GetProperty("optionColors")[0].GetString() != "rgb(29, 29, 31)"
                    && root.GetProperty("voiceOptions")[0].GetProperty("value").GetString() == "Kaveri"
                    && root.GetProperty("errors").GetArrayLength() == 0
                    && savedModel
                    && restoredRoot.GetProperty("model").GetString() == "timbre-v2.5"
                    && restoredRoot.GetProperty("voice").GetString() == "Kaveri";
                await web.CoreWebView2.ExecuteScriptAsync("document.querySelector('[data-k=\"gnaniTtsModel\"]').dispatchEvent(new Event('change', {bubbles:true}))");
                await Task.Delay(100);
                Result = ok && messages.Count > 0 ? 0 : 1;
                if (Environment.GetEnvironmentVariable("SILLY_WEB_CAPTURE") is { Length: > 0 } tab)
                {
                    await web.CoreWebView2.ExecuteScriptAsync($"st.tab('{tab}');");
                    await Task.Delay(250);
                    if (tab == "brain")
                        await web.CoreWebView2.ExecuteScriptAsync("document.querySelector('[data-k=\"aiPrimary\"]')?.open = true");
                    await Task.Delay(250);
                    var path = Path.Combine(Path.GetTempPath(), $"silly-settings-{tab}.png");
                    await using var file = File.Create(path);
                    await web.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png, file);
                    Console.WriteLine($"WEB_SCREENSHOT={path}");
                }
            }
            catch { Result = 1; }
            Exit();
        }

        void Exit()
        {
            host.Close();
            ExitThread();
        }
    }
}
