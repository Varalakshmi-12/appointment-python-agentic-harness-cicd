import { useEffect, useState } from "react";
import API from "../api";
import { Link } from "react-router-dom";

const STATUS_OPTIONS = ["scheduled", "confirmed", "cancelled", "completed"];

export default function AppointmentList() {
  const [appointments, setAppointments] = useState([]);

  useEffect(() => {
    API.get("/appointments").then((res) => setAppointments(res.data));
  }, []);

  const handleStatusChange = async (id, status) => {
    await API.patch(`/appointments/${id}/status`, { status });
    setAppointments((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status } : a))
    );
  };

  return (
    <div>
      <h2>List Of Appointments</h2>
      <table>
        <thead>
          <tr>
            <th>Patient Name</th>
            <th>Phone</th>
            <th>Provider</th>
            <th>Email</th>
            <th>Time</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {appointments.map((a) => (
            <tr key={a.id}>
              <td>{a.patient_name}</td>
              <td>{a.patient_phone}</td>
              <td>{a.provider_name}</td>
              <td>{a.patient_email}</td>
              <td>{a.appointment_time}</td>
              <td>
                <select
                  value={a.status}
                  onChange={(e) => handleStatusChange(a.id, e.target.value)}
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <Link to={`/edit/${a.id}`}>Edit</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
        
        
      <Link to="/new" style={{ marginLeft: "10px" }}>
        New Appointment
          </Link>
    </div>
    
  );
}