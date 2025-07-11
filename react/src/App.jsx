import { useState } from 'react';
import LoginForm from './components/LoginForm';
import PatientList from './components/PatientList';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));

  return (
    <div>
      <h1>Vaccination Schedule</h1>
      {!token ? (
        <LoginForm onLogin={setToken} />
      ) : (
        <PatientList />
      )}
    </div>
  );
}

export default App;