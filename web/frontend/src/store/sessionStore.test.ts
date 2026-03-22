import { describe, it, expect, beforeEach } from 'vitest';
import { useSessionStore } from './sessionStore';

describe('sessionStore', () => {
  beforeEach(() => {
    useSessionStore.setState({ currentSessionId: null });
  });

  it('initial state: currentSessionId is null', () => {
    expect(useSessionStore.getState().currentSessionId).toBeNull();
  });

  it('setCurrentSessionId sets the session id', () => {
    useSessionStore.getState().setCurrentSessionId('abc');
    expect(useSessionStore.getState().currentSessionId).toBe('abc');
  });

  it('setCurrentSessionId(null) resets to null', () => {
    useSessionStore.getState().setCurrentSessionId('abc');
    useSessionStore.getState().setCurrentSessionId(null);
    expect(useSessionStore.getState().currentSessionId).toBeNull();
  });
});
