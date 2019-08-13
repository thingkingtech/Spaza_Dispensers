#from pad4pi import rpi_gpio
import time
import sys
import RPi.GPIO as GPIO
from keypad import keypad
import logging
from hx711 import HX711
from decimal import Decimal, ROUND_DOWN

end_weight = None

###########################UNIQUE DATA FOR EACH DISPENSER################
gperR = 59
UID = "tmb2tas1d4"
Product = "Tastic Rice"
Store = "Spaza_2"
Location = "Tembisa"
#########################################################################

# Load Cell #
hx = HX711(5, 6)
hx.set_reading_format("MSB", "MSB")
hx.set_reference_unit(-210)
tare = 1865
hx.reset()

#########

buzzer = 4
led = 3

servoPIN = 19
switch = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(servoPIN, GPIO.OUT)
GPIO.setup(switch, GPIO.OUT)

GPIO.setup(buzzer, GPIO.OUT)
#p = GPIO.PWM(servoPIN, 50)
#p.start(2.5)
#p.ChangeDutyCycle(2.5)

###################################################################################3##LCD

# Define GPIO to LCD mapping
LCD_RS = 7
LCD_E  = 8
LCD_D4 = 26
LCD_D5 = 13
LCD_D6 = 16
LCD_D7 = 12
LED_ON = 15
 
# Define some device constants
LCD_WIDTH = 20    # Maximum characters per line
LCD_CHR = True
LCD_CMD = False
 
LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line
 
# Timing constants
E_PULSE = 0.0005
E_DELAY = 0.0005

def lcd_init():
  # Initialise display
  lcd_byte(0x33,LCD_CMD) # 110011 Initialise
  lcd_byte(0x32,LCD_CMD) # 110010 Initialise
  lcd_byte(0x06,LCD_CMD) # 000110 Cursor move direction
  lcd_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off
  lcd_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
  lcd_byte(0x01,LCD_CMD) # 000001 Clear display
  time.sleep(E_DELAY)
 
def lcd_byte(bits, mode):
  # Send byte to data pins
  # bits = data
  # mode = True  for character
  #        False for command
 
  GPIO.output(LCD_RS, mode) # RS
 
  # High bits
  GPIO.output(LCD_D4, False)
  GPIO.output(LCD_D5, False)
  GPIO.output(LCD_D6, False)
  GPIO.output(LCD_D7, False)
  if bits&0x10==0x10:
    GPIO.output(LCD_D4, True)
  if bits&0x20==0x20:
    GPIO.output(LCD_D5, True)
  if bits&0x40==0x40:
    GPIO.output(LCD_D6, True)
  if bits&0x80==0x80:
    GPIO.output(LCD_D7, True)
 
  # Toggle 'Enable' pin
  lcd_toggle_enable()
 
  # Low bits
  GPIO.output(LCD_D4, False)
  GPIO.output(LCD_D5, False)
  GPIO.output(LCD_D6, False)
  GPIO.output(LCD_D7, False)
  if bits&0x01==0x01:
    GPIO.output(LCD_D4, True)
  if bits&0x02==0x02:
    GPIO.output(LCD_D5, True)
  if bits&0x04==0x04:
    GPIO.output(LCD_D6, True)
  if bits&0x08==0x08:
    GPIO.output(LCD_D7, True)
 
  # Toggle 'Enable' pin
  lcd_toggle_enable()
 
def lcd_toggle_enable():
  # Toggle enable
  time.sleep(E_DELAY)
  GPIO.output(LCD_E, True)
  time.sleep(E_PULSE)
  GPIO.output(LCD_E, False)
  time.sleep(E_DELAY)
 
def lcd_string(message,line,style):
      if style==1:
        message = message.ljust(LCD_WIDTH," ")
      elif style==2:
        message = message.center(LCD_WIDTH," ")  
      elif style==3:
        message = message.rjust(LCD_WIDTH," ")
 
      lcd_byte(line, LCD_CMD)
 
      for i in range(LCD_WIDTH):
        lcd_byte(ord(message[i]),LCD_CHR)

###########################################################################LCD

logging.basicConfig(filename=UID+'_dispenser_log_'+time.strftime("%Y%m%d")+'.csv', filemode='a', format='%(asctime)s %(message)s', datefmt="%Y-%m-%d; \t %H:%M:%S;", level=logging.INFO)

logfile = open(UID+"_dispenser_log_"+time.strftime("%Y%m%d")+".csv", "a")
logfile.write("Date; \tTime; \tMessage; \tQuantity; \tUnit; \tUID; \tStore; \tLocation; \tProduct; \tTransaction;\n")
logfile.close()

GPIO.setwarnings(False)

kp = keypad(columnCount = 3)

def solenoidon():
    GPIO.output(switch, GPIO.HIGH)
    servo = GPIO.PWM(servoPIN, 50)
    servo.start(12)
    time.sleep(1)
    servo.ChangeDutyCycle(12.5)

    
def solenoidoff():
    GPIO.output(switch, GPIO.LOW)
    
def beepbeep():
    noiseon()
    time.sleep(0.1)
    noiseoff()
    time.sleep(0.1)
    noiseon()
    time.sleep(0.1)
    noiseoff()

def dispense(start_weight, amount):
    
    global rands
    global dispensed
    global end_weight
    global transnum
    
    rands =0
    
    transfile = open('transnum.txt', 'r')
    transnum = transfile.readline()
    transfile.close()
    if transnum == None or '':
        transnum = 0
    transnum = int(transnum)
    transnum += 1
    transfile = open('transnum.txt', 'w')
    transfile.write(str(transnum))
    transfile.close()
    transnum = str(transnum)
        
    if end_weight == None:
        end_weight = start_weight
    
    if start_weight > end_weight + 100:
        logging.info('\tRefill detected;\t' + '-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
        logging.info('\tAmount Refilled; \t' + str(start_weight - end_weight) + ';\t g; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
        
    beepbeep()
    ledon()
    #solenoidon()
    
    if amount == 0:                                                     # FREE FLOW
        
        digit = None
        logging.info('\tSTART; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum+ ";")
        
        transactions = open('transactions_2.txt', 'a')
        transactions.write("START " + time.strftime("%Y%m%d-%H%M") + "\n")
        transactions.close()
        
        while digit != "#":
           
            digit = kp.getKey()
            time.sleep(0.3)
            # Free Flow mode
            # Dispense
            solenoidon()
            current_weight = hx.get_weight(5) - tare
            time.sleep(0.1)
         
            dispensed = float(start_weight) - float(current_weight)
            rands = float(dispensed/gperR)
            rands = Decimal(rands).quantize(Decimal('.01'), rounding=ROUND_DOWN)
            
            dispensed = round(dispensed, 0)
            dispensed = max(0, dispensed)
            rands = max(0, rands)
            
            lcd_string("Dispenser Active",LCD_LINE_1,2)
            lcd_string("R"+str(rands),LCD_LINE_2,2)
            lcd_string(str(int(dispensed))+"g",LCD_LINE_3,2)            
            lcd_string("Hold # to cancel",LCD_LINE_4,2)
            
            digit = kp.getKey()
            time.sleep(0.2)
          
        if digit == "#":
                beepbeep()
                ledoff()
                solenoidoff()
                
                transaction_end = open('transactions_2.txt', 'a')
                transaction_end.write("END " + time.strftime("%Y%m%d-%H%M") + "\n")
                transaction_end.close()
                
                lcd_string("Dispensing Complete",LCD_LINE_1,2)
                lcd_string("Total: R"+str(rands),LCD_LINE_2,2)
                lcd_string("Total: "+str(int(dispensed))+"g",LCD_LINE_3,2)       
                lcd_string("Push * to continue",LCD_LINE_4,2)
                
                digit = None
                
                while digit != "*":
                    digit = kp.getKey()
                    time.sleep(0.2)
                
                
                logging.info('\tR dispensed; \t' + str(rands) + ';\t R; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tg dispensed; \t' + str(dispensed) + ';\t g; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tStart quantity; \t' + str(start_weight) + ";\t g; \t" + UID + ";\t" + Store + ";\t" + Location +";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tCurrent quantity; \t' + str(max(0,current_weight)) + ";\t g; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tEND; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                
                main()
                                      
    elif amount < start_weight and amount > 0:                          # Value Entered
        
        digit = None
            
        digit = kp.getKey()
        
        time.sleep(0.3)
        
        logging.info('\tSTART; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")

        transactions_start = open('transactions_2.txt', 'a')
        transactions_start.write("START " + time.strftime("%Y%m%d-%H%M") + "\n")
        transactions_start.close

        end_weight = start_weight - amount
        time.sleep(0.3)
        current_weight = hx.get_weight(5) - tare
        
        current_weight = max(0, current_weight)
            
        dispensed = int(start_weight) - int(current_weight)
        
        while dispensed <= amount and digit != "#":
            #Dispense
            solenoidon()
            
            digit = kp.getKey()
            
            time.sleep(0.3)
            current_weight = hx.get_weight(5) - tare
                
            dispensed = float(start_weight) - float(current_weight)
            
            
            rands = float(dispensed/gperR)
            rands = max(0, rands)
            rands = round(rands, 2)
            rands = str(rands)
             
            dispensed = max(0, dispensed)
            
            lcd_string("Dispenser Active",LCD_LINE_1, 2)
            lcd_string("R"+rands,LCD_LINE_2,2)
            lcd_string(str(int(dispensed))+"g",LCD_LINE_3,2) 
            lcd_string("Hold # to cancel",LCD_LINE_4,2) 
            
            digit = kp.getKey()
            
        if current_weight <= end_weight or digit == "#":
            beepbeep()
            ledoff()
            solenoidoff()
            
            lcd_string("Dispensing Complete",LCD_LINE_1,2)
            lcd_string("Total: R"+str(rands),LCD_LINE_2,2)
            lcd_string("Total: "+str(int(dispensed))+"g",LCD_LINE_3,2)       
            lcd_string("Push * to continue",LCD_LINE_4,2)
            
            if digit == "#":
                logging.info('\t# Pressed; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tR dispensed; \t' + rands + ';\t R; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tg dispensed; \t' + str(int(dispensed)) + ';\t g; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                #logging.info('R' + str(rands) + ' dispensed = ' + str(dispensed) + 'ml \t NA \t NA \t' + UID)
                logging.info('\tStart quantity; \t' + str(start_weight) + ";\t g; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tCurrent quantity; \t' + str(max(0,current_weight)) + ";\t g; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tEND; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
 
                transactions_ending = open('transactions_2.txt', 'a')
                transactions_ending.write("END " + time.strftime("%Y%m%d-%H%M") + "\n")
                transactions_ending.close() 
                
            elif current_weight <= end_weight:
                
                logging.info('\tR dispensed; \t' + str(rands) + ';\t R; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tg dispensed; \t' + str(dispensed) + ';\t g; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                #logging.info('R' + str(rands) + ' dispensed = ' + str(dispensed) + 'ml \t NA \t NA \t' + UID)
                logging.info('\tStart quantity; \t' + str(start_weight) + ";\t g; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tCurrent quantity; \t' + str(max(0,current_weight)) + ";\t g; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
                logging.info('\tEND; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
            
                transactions_ending = open('transactions_2.txt', 'a')
                transactions_ending.write("END " + time.strftime("%Y%m%d-%H%M") + "\n")
                transactions_ending.close()            
            
            digit = None
            
            while digit != "*":
                digit = kp.getKey()
                time.sleep(0.1)
                digit = kp.getKey()
            
            
            
    elif amount > start_weight:                                         # Insufficient stock
        logging.info("\tLow Stock; \t-; \t -; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
        logging.info("\tRequested; \t" + str(amount) + ";\t g; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";") 
        logging.info("\tAvialable; \t" + str(start_weight) + ";\t g; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + transnum + ";")
        
        beepbeep()
        ledoff()
        solenoidoff()
        
        digit = None
        
        while digit != "*":
            digit = kp.getKey()
            time.sleep(0.2)    
            
            lcd_string("Insufficient Stock",LCD_LINE_1,2)
            lcd_string(str(max(0,start_weight)) + "g remaining",LCD_LINE_2,2)
            lcd_string("Please re-fill",LCD_LINE_3,2)       
            lcd_string("Push * to continue",LCD_LINE_4,2)
            
            digit = kp.getKey()
        
def noiseon():
    
    GPIO.output(buzzer, GPIO.HIGH)        

def noiseoff():
    
    GPIO.output(buzzer, GPIO.LOW)

def ledon():
    GPIO.output(led, GPIO.HIGH)
    
def ledoff():
    GPIO.output(led, GPIO.LOW)
    
def main():
    
    GPIO.setmode(GPIO.BCM)       # Use BCM GPIO numbers
    GPIO.setup(LCD_E, GPIO.OUT)  # E
    GPIO.setup(LCD_RS, GPIO.OUT) # RS
    GPIO.setup(LCD_D4, GPIO.OUT) # DB4
    GPIO.setup(LCD_D5, GPIO.OUT) # DB5
    GPIO.setup(LCD_D6, GPIO.OUT) # DB6
    GPIO.setup(LCD_D7, GPIO.OUT) # DB7
    GPIO.setup(LED_ON, GPIO.OUT) # Backlight enable
    
    GPIO.setup(buzzer, GPIO.OUT)   
    GPIO.setup(led, GPIO.OUT)      # LED and Buzzer
 
    lcd_init()
    
    
    amount = ""
    
    solenoidoff()
    
    #print "Enter 1 for Free Mode, 2 for R Mode or 3 for ml Mode"
    
    lcd_string("1: Free Flow",LCD_LINE_1,1)
    lcd_string("2: R Value",LCD_LINE_2,1)
    lcd_string("3: g Value",LCD_LINE_3,1)
    lcd_string("#: Cancel",LCD_LINE_4,1)
    
    logging.info('\tIDLE; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
    
    digit = None
    while digit == None:                                                ############# Wait for key press
        digit = kp.getKey()
    
    if digit >= 1 and digit <= 3:                                       ############# 1,2 or 3 entered
        
        if digit == 1:                                                  ############# FREE MODE
            logging.info('\tFree Mode; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
            #print "FREE FLOW - Push * to end"
            time.sleep(0.3)
            start_weight = hx.get_weight(5) - tare 
           
            digit = None

            dispense(start_weight, 0)

            time.sleep(0.1)

        elif digit == 2:                                                ############# R MODE
            logging.info('\tR Mode; \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
            time.sleep(0.5)
            #print "Enter Rands followed by *"
            
            lcd_string("Enter Rands",LCD_LINE_1,2)
            lcd_string("R",LCD_LINE_2,2)
            lcd_string("Press * to continue",LCD_LINE_3,2)            
            lcd_string("Hold # to cancel",LCD_LINE_4,2)
            
            digit = None
            
            while digit != "*":
          
                while digit == None:
                    digit = kp.getKey()
                    time.sleep(0.2)
                
                    if digit >= 0 and digit <= 9:
                        amount += str(digit)
                        #print digit 
                        time.sleep(0.1)
                        digit=None
                        
                        lcd_string("R"+amount,LCD_LINE_2,2)

                        
                    elif digit == "*":
                        break
                        
                    elif digit == "#":
                        logging.info("\t# pressed; \t-; \t-; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                        main()
                            
            amount = amount.lstrip("0")                                 # Remove leading zeros
            
            if amount == "":
                
                lcd_string("",LCD_LINE_1,2)
                lcd_string("Nothing Entered",LCD_LINE_2,2)
                lcd_string("",LCD_LINE_3,1)            
                lcd_string("",LCD_LINE_4,1)
                #print "You didn't enter anything?"
                logging.info('\tNothing Entered;  \t -; \t -; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                main()
            
            elif int(amount) > 0:

                #print "R" + amount + " has been selected"
                
                value = int(amount)*gperR
                value = str(value)
                
                lcd_string("R"+amount,LCD_LINE_1,2)
                lcd_string(value+"g",LCD_LINE_2,2)                          # 
                lcd_string("Push * to continue",LCD_LINE_3,2)            
                lcd_string("Hold # to cancel",LCD_LINE_4,2)
                
                logging.info('\tRequested; \t' + amount + ';\t R; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                #print "Press * to continue, or # to cancel"
                digit = None
                
                while digit != "*" and digit!= "#":
                    digit = kp.getKey()
                    time.sleep(0.2)
                    digit = kp.getKey()
                 
                if digit == "*":
                     
                    logging.info('\tConfirmed; \t' + amount + ';\t R; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                    
                    #print "Dispenser active"
                    time.sleep(0.3)
                    start_weight = hx.get_weight(5) - tare 
                    
                    dispense(start_weight, int(value))
                    
                    #print "R" + amount + " has been dispensed, press * to continue"
                    
                    
                    digit = None
                    
                    while digit != "*":
                        digit = kp.getKey()
                        time.sleep(0.2)
                        
                    if digit == "*":
                        main()
    
                elif digit == "#":
                    logging.info("\t# pressed; \t-; \t-; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                    main()
    
            else:
                
                lcd_string("",LCD_LINE_1,2)
                lcd_string("Nothing Entered",LCD_LINE_2,2)
                lcd_string("",LCD_LINE_3,1)            
                lcd_string("",LCD_LINE_4,1)
                
                logging.info('\tNothing entered;  \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                main()
    
        elif digit == 3:                                                ############# ml MODE
             logging.info('\tg Mode; \t-; \t -; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
             time.sleep(0.5)
            # print "Enter ml followed by *"
            
             lcd_string("Enter g",LCD_LINE_1,2)
             lcd_string("g",LCD_LINE_2,2)
             lcd_string("Press * to continue",LCD_LINE_3,2)            
             lcd_string("Hold # to cancel",LCD_LINE_4,2)
            
             digit = None
            
             while digit != "*":
          
                 while digit == None:
                     digit = kp.getKey()
                     time.sleep(0.2)
                
                     if digit >= 0 and digit <= 9:
                         amount += str(digit)
                         #print digit 
                         
                         lcd_string(amount+"g",LCD_LINE_2,2)
                         
                         time.sleep(0.1)
                         digit=None
                     
                     elif digit == "*":
                         break
                         
                     elif digit == "#":
                         logging.info("\t# pressed;  \t-; \t-; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                         main()
    
             amount = amount.lstrip("0")                                # Remove leading zeros
            
             if amount == "":
                 #print "You didn't enter anything?"
                 
                 lcd_string("",LCD_LINE_1,2)
                 lcd_string("Nothing Entered",LCD_LINE_2,2)
                 lcd_string("",LCD_LINE_3,1)            
                 lcd_string("",LCD_LINE_4,1)
                 
                 logging.info('\tNothing entered;  \t-; \t-; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                 main()
            
             elif int(amount) > 0:                                      

                 value = float(amount)/gperR
                 value = Decimal(value).quantize(Decimal('.01'), rounding=ROUND_DOWN)
                # value = round(value, 3)
                 value = str(value)
                 
                 lcd_string(amount+"g",LCD_LINE_1,2)
                 lcd_string("R"+value,LCD_LINE_2,2)
                 lcd_string("Push * to continue",LCD_LINE_3,2)            
                 lcd_string("Hold # to cancel",LCD_LINE_4,2)
                 
                 logging.info('\tRequested; \t' + amount + ';\t g; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                 #print "Press * to continue, or # to cancel"
                 digit = None
                 
                 while digit != "*" and digit!= "#":
                    digit = kp.getKey()
                    time.sleep(0.2)
                 
                 if digit == "*":
                     
                    logging.info('\tConfirmed; \t' + amount + ';\t g; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                   # print "Dispenser active"
                    time.sleep(0.3)
                    start_weight = hx.get_weight(5) - tare 
                    dispense(start_weight, int(amount))
                    
                    #print "Dispenser active"
                    
                    #logging.info("\tDe-activated  \t- \t- \t" + UID + "\t" + Store + "\t" + Location + "\t" + Product)
                    
                    
                    digit = None
                    
                    while digit != "*":
                        digit = kp.getKey()
                        time.sleep(0.2)
                        
                    if digit == "*":
                        main()
    
                 elif digit == "#":
                     logging.info("\t# pressed; \t-; \t-; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                     main()
    
             else:
                
                
                 lcd_string("",LCD_LINE_1,2)
                 lcd_string("Nothing Entered",LCD_LINE_2,2)
                 lcd_string("",LCD_LINE_3,1)            
                 lcd_string("",LCD_LINE_4,1)
                 #print "No amount entered"
                 logging.info('\tNo amount entered; \t -; \t -; \t' + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
                 main()
            
    else:                                                               ############# Incorrect key press
        digit = None
        time.sleep(0.2)
        logging.info("\tBad Button; \t -; \t -; \t" + UID + ";\t" + Store + ";\t" + Location + ";\t" + Product + ";\t" + "NULL;")
        main()

while True:
    try:
        main()
    
    except (KeyboardInterrupt, SystemExit):
        print "dead"
        lcd_byte(0x01, LCD_CMD)
        lcd_string("Goodbye!",LCD_LINE_1,2)
        GPIO.cleanup()
        noiseoff()
        solenoidoff()
        beepbeep()
        ledoff()
