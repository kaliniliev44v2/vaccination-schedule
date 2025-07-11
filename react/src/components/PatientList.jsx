import { useEffect, useState } from 'react';
import axios from '../api/axios';

export default function PatientList() {
  const [patients, setPatients] = useState([]);

  useEffect(() => {
    const fetchPatients = async () => {
      const response = await axios.get('/patients/', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      setPatients(response.data);
    };
    fetchPatients();
  }, []);

  return (
    <div>
      <h3>Пациенти</h3>
      <ul>
        {patients.map(p => (
          <li key={p.id}>{p.first_name} {p.last_name}</li>
        ))}
      </ul>
    </div>
  );
}