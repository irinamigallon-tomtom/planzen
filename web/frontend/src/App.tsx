import { useSessionStore } from './store/sessionStore';
import { UploadView } from './components/UploadView';
import { PlanEditor } from './components/PlanEditor';

function App() {
  const currentSessionId = useSessionStore((s) => s.currentSessionId);
  return currentSessionId ? <PlanEditor /> : <UploadView />;
}

export default App;
