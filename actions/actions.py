# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

import os
from typing import Dict, Text, Any, List,Optional
import logging
from dateutil import parser
import sqlalchemy as sa
from datetime import datetime
from rasa_sdk.types import DomainDict
import requests
import os
from dotenv import load_dotenv

from rasa_sdk.interfaces import Action
from rasa_sdk.events import (
    SlotSet,
    EventType,
    ActionExecuted,
    SessionStarted,
    Restarted,
    FollowupAction,
    UserUtteranceReverted
)

from actions.parsing import (
    parse_duckling_time_as_interval,
    parse_duckling_time,
    get_entity_details,
    parse_duckling_currency,
    get_previous_slot_value_from_tracker
)
from rasa_sdk import Tracker,FormValidationAction
from rasa_sdk.executor import CollectingDispatcher

from actions.custom_forms import CustomFormValidationAction

logger = logging.getLogger(__name__)

class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    @staticmethod
    def fetch_slots(tracker: Tracker) -> List[EventType]:
        """Collect slots that contain the user's name and phone number."""

        slots = []
        for key in ("PERSON", "phone", "email","age","dialed_phone" ):
            value = tracker.get_slot(key)
            if value is not None:
                slots.append(SlotSet(key=key, value=value))
        return slots

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
    
        print('In Sesion Start')
        
        # the session should begin with a `session_started` event
        events = [SessionStarted()]

        # any slots that should be carried over should come after the
        # `session_started` event
        slots = self.fetch_slots(tracker)
        slots.append(SlotSet(key="is_new_session", value='yes'))
       
        #print( tracker.get_slot("is_new_session"))
        
        channel = tracker.get_latest_input_channel()
       
        if  (channel=='twilio_voice'  or channel=='twilio'):
            dialed_phone = tracker.sender_id
            slots.append(SlotSet(key="dialed_phone", value=dialed_phone))
            SlotSet("dialed_phone", dialed_phone)
            #print('Dialed_Pone:' +  dialed_phone )
       
       
        events.extend(slots)
        print (slots)
        # an `action_listen` should be added at the end as a user message follows
        events.append(ActionExecuted("action_listen"))

        return events

class ValidateContactForm(CustomFormValidationAction):
    """Validates Slots of the tcontact_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_contact_form"

    async def required_slots(
        self,
        slots_mapped_in_domain: List[Text],
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Optional[List[Text]]:
        required_slots = slots_mapped_in_domain.copy()
        if ( tracker.get_slot("is_new_user")=='existing_user' and tracker.get_slot("PERSON")!='None' ):
            try:
                
                if 'PERSON' in required_slots:
                    required_slots.remove('PERSON')
                if 'is_the_person' not in required_slots:
                    required_slots.append('is_the_person')
            except:
                pass
        elif(tracker.get_slot("is_new_user")=='existing_user' and tracker.get_slot("phone")!='None'):   # Either New user or Existing User whose Name and Phone is not yet set
            try:
                
                if 'phone' in required_slots:
                    required_slots.remove('phone')
                if 'is_best_phone' not in required_slots:
                    required_slots.append('is_best_phone')
            except:
                pass
        else:
            
            if 'is_best_phone' in required_slots:
                required_slots.remove('is_best_phone')
            if 'is_the_person' in required_slots:
                required_slots.remove('is_the_person')

        if ( tracker.get_latest_input_channel()=='twilio_voice'):
            try:
                sender = tracker.sender_id
                #print(sender)
                if 'email' in required_slots:
                    required_slots.remove('email')
            except:
                pass
        
        if ( tracker.get_slot("is_the_person")=='no'):
            try:
                #print('in Not the Person - Removing is_best_phone')
                if 'phone' not in required_slots:
                    index = slots_mapped_in_domain.index('phone')
                    required_slots.insert(index,'phone')
                    #required_slots.append('phone')
                if 'PERSON' not in required_slots:
                    index = slots_mapped_in_domain.index('PERSON')
                    required_slots.insert(index,'PERSON')
                if 'is_best_phone' in required_slots:
                    required_slots.remove('is_best_phone')
                if 'is_the_person' in required_slots:
                    required_slots.remove('is_the_person')
            except Exception as e:
                print('In exception')
                print(e)
                pass
       
        print(required_slots)
        return required_slots

    async def validate_is_the_person(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'PERSON' slot"""
        # It is possible that both Spacy & DIET extracted the PERSON
        # Just pick the first one
        if isinstance(value, list):
            value = value[0]
        
       
        requested_slot = tracker.current_state()['slots']['requested_slot']
        if requested_slot == 'is_the_person':
            #return {"is_best_phone": value}
            #print(value)
            if(value=='no'):
                # person_value = next(tracker.get_latest_entity_values("PERSON"),None)
                # if isinstance(person_value, list):
                #     person_value = person_value[0]
                # else:
                #     person_value= None
                
                # print('person_value')
                # print(person_value)
                #dispatcher.utter_message("Ok! What is your name?")
                return {"is_the_person":value,"phone":None,"is_new_session":"no","PERSON":None,"age":None,"email":None}
                
            else:
                return {"is_the_person":value,"is_new_session":"no"}
        else:
            return {"is_the_person": get_previous_slot_value_from_tracker(tracker,"is_the_person")}

    async def validate_PERSON(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'PERSON' slot"""
        # It is possible that both Spacy & DIET extracted the PERSON
        # Just pick the first one
        print('In Validate Person')
        if isinstance(value, list):
            value = value[0]

        name = value.lower() if value else None
        #print('Name is' + name)
     
        requested_slot = tracker.current_state()['slots']['requested_slot']
        #print('Requested slot is:' + requested_slot)
        if requested_slot == 'PERSON':
            print('returning Person name:')
            print(name)
            return {"PERSON": name}
        else:
            prev_person = get_previous_slot_value_from_tracker(tracker,"PERSON")
            print('returning previous person' + prev_person )
            return {"PERSON": prev_person }
    
    async def explain_PERSON(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Explains 'Person' slot"""
        dispatcher.utter_message("You can say your full name. For example you can say, My Name is Rohit Sharma.")
        return {}

    async def validate_is_best_phone(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'PERSON' slot"""
        # It is possible that both Spacy & DIET extracted the PERSON
        # Just pick the first one
        if isinstance(value, list):
            value = value[0]
        
       
        requested_slot = tracker.current_state()['slots']['requested_slot']
        if requested_slot == 'is_best_phone':
            #return {"is_best_phone": value}
            #print(value)
            if(value=='no'):
                phone_value = next(tracker.get_latest_entity_values("phone"),None)
                if isinstance(phone_value, list):
                    phone_value = phone_value[0]
                else:
                    phone_value= None
                #dispatcher.utter_message("Ok! What is your phone number?")
       
                #print('phone_value')
                #print(phone_value)
                return {"is_best_phone":value, "phone":phone_value,"is_new_session":"no","age":None,"email":None}
                
            else:
                return {"is_best_phone":value,"is_new_session":"no"}
        else:
            return {"is_best_phone": get_previous_slot_value_from_tracker(tracker,"is_best_phone")}

    async def validate_phone(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'PERSON' slot"""
        # It is possible that both Spacy & DIET extracted the PERSON
        # Just pick the first one
        if isinstance(value, list):
            value = value[0]
        
       
        requested_slot = tracker.current_state()['slots']['requested_slot']
        if requested_slot == 'phone':
            return {"phone": value}
        else:
            return {"phone": get_previous_slot_value_from_tracker(tracker,"phone")}

    async def explain_phone(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Explains 'Person' slot"""
        dispatcher.utter_message("Full name is needed.")
        return {}   

    async def validate_email(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'PERSON' slot"""
        # It is possible that both Spacy & DIET extracted the PERSON
        # Just pick the first one
        if isinstance(value, list):
            value = value[0]
        
        requested_slot = tracker.current_state()['slots']['requested_slot']
        #print(requested_slot)
        #print(value)
        if requested_slot == 'email':
            return {"email": value}
        else:
            return {"email": get_previous_slot_value_from_tracker(tracker,"email")}

       
        
    async def explain_email(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Explains 'Person' slot"""
        dispatcher.utter_message("You need to provide a valid email address.")
        return {}  

    async def validate_age(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        #print('in validate age')
        if isinstance(value, list):
            for bday in value:
                try:
                    d = datetime.strptime(bday, '%Y-%m-%dT%H:%M:%S.%f%z')
                    #print(d)
                    return({"age":bday})
                except ValueError as ve:
                    print(str(ve))


    async def explain_age(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Explains 'Person' slot"""
        dispatcher.utter_message("A valid birth date is needed. For example you can say January 10th 1956 ")
        return {}     
        """Validates value of 'time' slot"""
        # timeentity = get_entity_details(tracker, "time")
        # print(timeentity)
        # parsedtime = timeentity and parse_duckling_time(timeentity)
        # print(timeentity)
        # if not parsedtime:
        #     dispatcher.utter_message(response="utter_no_transactdate")
        #     return {"time": None}
        # return parsedtime
        
class ActionVerifyNewUser(Action):
    """Asks to switch back to previous form"""

    def name(self) -> Text:
        return "action_verify_new_user"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        """Executes the custom action"""
        print('in action_verify_new_user ')
        name = tracker.get_slot("PERSON")
        phone = tracker.get_slot("phone")
        email = tracker.get_slot("email")
        age = tracker.get_slot("age")
        is_new_user= 'new_user'

        if tracker.get_latest_input_channel()=='twilio_voice' and name!= None and phone!= None and age!=None :
            is_new_user= 'existing_user'
        elif name!= None and phone!= None and age!=None and email!=None:
            is_new_user= 'existing_user'
        
        return [SlotSet("is_new_user", is_new_user)]

class ActionSetChannel(Action):
    """Asks to switch back to previous form"""

    def name(self) -> Text:
        return "action_set_channel"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        """Executes the custom action"""
        print('in action_set_channel ')
        channel = tracker.get_latest_input_channel()
        print('channel is:')
        print(channel)
        return [SlotSet("channel", channel)]
 
class ActionSetFaqSlot(Action):
    """Returns the chitchat utterance dependent on the intent"""

    def name(self) -> Text:
        return "action_set_faq_slot"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[EventType]:
        text = tracker.latest_message['text']
        print(text)
        load_dotenv()
        url = os.getenv('luis_url')
        auth_key = os.getenv('luis_auth_key')
        print(url)
        #print(auth_key)
        payload="{'question':'"+text+"'}"
        headers = {
        'Authorization': 'EndpointKey '+os.getenv('luis_auth_key'),
        'Content-type': 'application/json'
         }

        response = requests.request("POST", url, headers=headers, data=payload).json()
        #print(response['answers'][0]['answer'])
        response_text= str(response['answers'][0]['answer']).replace('eHealth','MedicareDialog')
        dispatcher.utter_message(response_text)
        return [SlotSet("faq", "yes")]
