# J.A.R.V.I.S Mobile (Android + iOS)

This directory is the first Flutter client foundation for Android and iOS. The existing Python/Tkinter application remains the Windows desktop client.

## Current mobile capabilities

- OpenAI-compatible chat-completions API.
- Configurable HTTPS endpoint and model.
- API key stored through `flutter_secure_storage`; endpoint and model preferences stored separately.
- Non-generative `/models` connectivity check.
- Bounded network timeouts and provider-neutral error messages.
- Provider URL validation rejects plain HTTP, embedded credentials, query strings, fragments, and phone-localhost endpoints.
- Conversation messages remain in memory and are not persisted by this initial client.

## Important limitations

This is an initial mobile chat client, not full feature parity with the Windows desktop agent. It does not control desktop applications, run Windows tools, access phone-wide data, or execute arbitrary commands. Those features require platform-specific, permission-gated integrations and a shared authenticated service. Do not put provider keys into source code or commit them.

## Build

Install Flutter stable and Android Studio for Android, or Xcode on macOS for iOS. From this directory:

```sh
flutter pub get
flutter analyze
flutter test
flutter run
```

Android release builds need a configured signing key. iOS builds need macOS/Xcode and appropriate signing and App Store credentials. No signed release artifact is committed by this source PR.
