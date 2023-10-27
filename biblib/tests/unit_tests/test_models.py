"""
Tests the underlying models of the database
"""

import unittest
from biblib.models import Library, MutableDict, Notes
from biblib.tests.base import TestCaseDatabase
from biblib.biblib_exceptions import BibcodeNotFoundError, DuplicateNoteError
import pytest


class TestLibraryModel(TestCaseDatabase):                                                                                                                                                                                                                                                                     
    """
    Class for testing the methods usable by the Library model
    """

    def test_get_bibcodes_from_model(self):
        """
        Checks that the get_bibcodes method works as expected
        """
        lib = Library(bibcode={'1': {}, '2': {}, '3': {}})
        with self.app.session_scope() as session:
            session.add(lib)
            session.commit()

            self.assertUnsortedEqual(lib.get_bibcodes(), ['1', '2', '3'])

    def test_adding_bibcodes_to_library(self):
        """
        Checks that the custom add/upsert command works as expected
        """
        # Make fake library
        bibcodes_list_1 = {'1': {}, '2': {}, '3': {}}
        bibcodes_list_2 = ['2', '2', '3', '4', '4']
        expected_bibcode_output = ['1', '2', '3', '4']

        lib = Library(bibcode=bibcodes_list_1)
        with self.app.session_scope() as session:
            session.add(lib)
            session.commit()

            lib.add_bibcodes(bibcodes_list_2)
            session.add(lib)
            session.commit()

            self.assertUnsortedEqual(lib.get_bibcodes(), expected_bibcode_output)

    def test_adding_bibcode_if_not_commited_to_library(self):
        """
        Checks that bibcodes are add correctly if the library has not been
        commited to the db yet.
        """
        bibcodes_list = ['1', '2', '3', '4']

        lib = Library()
        lib.add_bibcodes(bibcodes_list)
        with self.app.session_scope() as session:
            session.add(lib)
            session.commit()

            self.assertEqual(lib.bibcode, {k: {"timestamp":lib.bibcode[k]["timestamp"]} for k in bibcodes_list})
            self.assertUnsortedEqual(lib.get_bibcodes(), bibcodes_list)

    def test_removing_bibcodes_from_library(self):
        """
        Checks that bibcodes get removed from a library correctly
        """
        # Stub data
        bibcodes_list_1 = {'1': {}, '2': {}, '3': {}}
        expected_list = ['2', '3']

        lib = Library(bibcode=bibcodes_list_1)
        with self.app.session_scope() as session:
            session.add(lib)
            session.commit()

            lib.remove_bibcodes(['1'])
            session.add(lib)
            session.commit()

            self.assertUnsortedEqual(lib.get_bibcodes(), expected_list)

    def test_coerce(self):
        """
        Checks the coerce for SQLAlchemy works correctly
        """
        mutable_dict = MutableDict()

        with self.assertRaises(ValueError):
            mutable_dict.coerce('key', 2)

        new_type = mutable_dict.coerce('key', {'key': 'value'})
        self.assertIsInstance(new_type, MutableDict)

        same_list = mutable_dict.coerce('key', mutable_dict)
        self.assertEqual(same_list, mutable_dict)

    def test_create_unique_note(self): 
        lib = Library(bibcode={'1': {}, '2': {}, '3': {}}, public=True, description="Test description")
        with self.app.session_scope() as session: 
            session.add(lib) 
            session.commit()

            note1 = Notes.create_unique(session, content="Test content 1", bibcode="1", library=lib)
            session.add(note1) 
            session.commit() 

            with self.assertRaises(DuplicateNoteError):
                note2 = Notes.create_unique(session, content="Test content 2", bibcode="1", library=lib) 
                session.add(note2)
                session.commit()
            
            existing_notes = session.query(Notes).filter_by(bibcode="1", library_id=lib.id).all() 
            self.assertEqual(len(existing_notes), 1) 
            self.assertEqual(existing_notes[0].content, "Test content 1") 
            self.assertEqual(lib.notes, [note1])

    def test_create_unique_bibcode_not_in_library(self):
       
        lib = Library(bibcode={'1': {}, '2': {}}, public=True, description="Test description")
        with self.app.session_scope() as session: 
            session.add(lib) 
            session.commit()

            with self.assertRaises(BibcodeNotFoundError) as context:
                note = Notes.create_unique(session, content="Test content 1", bibcode="3", library=lib) 
                session.add(note)
                session.commit()

            self.assertUnsortedEqual(lib.get_bibcodes(), ['1', '2'])
            self.assertEqual(lib.notes, [])
            self.assertIn("Bibcode 3 not found", context.exception.args[0])  

    def test_create_unique_raises_exception(self):
        
        lib = Library(bibcode={'1': {}, '2': {}}, public=True, description="Test description")
        with self.app.session_scope() as session: 
            session.add(lib) 
            session.commit()
            # Attempt to create a note with a bibcode that is not in the library, which should raise a ValueError
            with pytest.raises(Exception) as exc_info:
                note = Notes.create_unique(session, "Note content", "NonExistentBibcode", lib)
                session.add(note)
                session.commit()

            # Check that the exception message matches the expected message
            self.assertIn('Bibcode NonExistentBibcode not found', str(exc_info.value))       

    def test_library_notes_relationship(self): 
        lib = Library(bibcode={'1': {}, '2': {}}, public=True, description="Test description")
        
        with self.app.session_scope() as session: 
            session.add(lib) 
            session.commit()
            note1 = Notes.create_unique(session, content="Note 1 Content", bibcode="1", library=lib)
            note2 = Notes.create_unique(session, content="Note 2 Content", bibcode="2", library=lib)
            session.add_all([note1, note2])
            session.commit()
            
            self.assertEqual(lib.notes, [note1, note2])

            session.delete(lib) 
            session.commit() 

            self.assertEqual(session.query(Notes).count(), 0)
            self.assertEqual(session.query(Library).count(), 0)

    def test_remove_bibcodes_remove_notes(self): 
        lib = Library(bibcode={'1': {}, '2': {}}, public=True, description="Test description")
        
        with self.app.session_scope() as session: 
            session.add(lib) 
            session.commit()
            note1 = Notes.create_unique(session, content="Note 1 Content", bibcode="1", library=lib)
            note2 = Notes.create_unique(session, content="Note 2 Content", bibcode="2", library=lib)
            session.add_all([note1, note2])
            session.commit()

            self.assertEqual(lib.notes, [note1, note2])
            self.assertEqual(session.query(Notes).count(), 2)


            lib.remove_bibcodes(['1', '2'])

            self.assertEqual(session.query(Notes).count(), 0)

    def test_change_bibcodes_orphan_notes(self): 
        lib = Library(bibcode={'1': {}, '2': {}}, public=True, description="Test description")
        
        with self.app.session_scope() as session: 
            session.add(lib) 
            session.commit()
            note1 = Notes.create_unique(session, content="Note 1 Content", bibcode="1", library=lib)
            session.add(note1)
            session.commit()
            self.assertEqual(lib.notes, [note1])
            self.assertEqual(session.query(Notes).count(), 1)


            lib.bibcode = {'2': {}, '3': {}}

            self.assertEqual(lib.notes, [note1])
            self.assertEqual(session.query(Notes).count(), 1)
            self.assertEqual(lib.notes[0].bibcode, '1')



            
            

        

    
if __name__ == '__main__':
    unittest.main(verbosity=2)
