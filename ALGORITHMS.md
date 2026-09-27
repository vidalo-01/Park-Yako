# Park Yako – Algorithms

## 1. Slot Management Algorithm

### Input
Parking slot records.

### Steps
1. Load all parking slots.
2. Check the status of each slot.
3. If a slot is available, display it as available.
4. If a slot is occupied, display it as occupied.
5. Update the display when a vehicle enters or exits.

### Output
Current parking slot availability.

---

## 2. Vehicle Entry Algorithm

### Input
Vehicle registration number.

### Steps
1. Receive the vehicle registration number.
2. Check whether the vehicle is already parked.
3. Check whether a parking slot is available.
4. If no slot is available, display "Parking Full".
5. Select the next available parking slot.
6. Record the vehicle registration number.
7. Record the entry time.
8. Assign the parking slot to the vehicle.
9. Save the parking session in the database.
10. Update the slot status to occupied.
11. Display the allocated slot.

### Output
Vehicle assigned to a parking slot and parking session recorded.

---

## 3. Fee Calculation Algorithm

### Input
Vehicle entry time and exit time.

### Steps
1. Retrieve the vehicle's entry time.
2. Record the exit time.
3. Calculate the total parking duration.
4. Apply the parking tariff.
5. Calculate the amount payable.
6. Display the amount to the customer.

### Output
Total parking fee.

---

## 4. Vehicle Exit and Payment Algorithm

### Input
Vehicle registration number.

### Steps
1. Find the active parking session.
2. Retrieve the entry time.
3. Record the exit time.
4. Calculate the parking duration.
5. Calculate the parking fee.
6. Request payment.
7. Wait for payment confirmation.
8. If payment is unsuccessful, keep the session active.
9. If payment is successful, mark the session as completed.
10. Release the parking slot.
11. Update the database.
12. Open the simulated barrier.

### Output
Completed parking session and released parking slot.

---

## 5. M-Pesa Payment Algorithm

### Input
Customer phone number and parking fee.

### Steps
1. Receive the customer's phone number.
2. Convert the number into the required Kenyan format.
3. Calculate the amount to be paid.
4. Send an M-Pesa STK Push request.
5. Set the payment status to pending.
6. Wait for the M-Pesa callback.
7. Check the payment result.
8. If payment fails, do not open the barrier.
9. If payment succeeds, record the successful payment.
10. Complete the parking session.
11. Open the simulated barrier.

### Output
Payment confirmed and barrier opened.

---

## 6. Barrier Control Algorithm

### Input
Successful payment confirmation.

### Steps
1. Receive payment confirmation.
2. Check that the payment was successful.
3. If payment is successful, open the simulated barrier.
4. Allow the vehicle to exit.
5. Release the allocated parking slot.
6. Update the parking session.

### Output
Barrier opened and parking slot released.
