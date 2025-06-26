import os
import json

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

#menu 
TASKS_FILE = 'tasks.json'
tasks = []

def load_tasks():
    global tasks
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r') as f:
            try:
                tasks = json.load(f)
            except json.JSONDecodeError:
                tasks = []

def save_tasks():
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

def display_tasks():
    if not tasks:
        print("No tasks to show.")
    else:
        for idx, task in enumerate(tasks, 1):
            status = "✅ Done" if task["done"] else "❌ Not done"
            print(f"{idx}. {task['task']} - {status}")

def menu(): 
    while True:
        clear_screen()
        print("Welcome to the Menu!")
        print("1. Add a task")
        print("2. View all tasks ")
        print("3. Mark a task as complete")
        print("4. Remove a task")
        print("5. Edit a task")
        print("6. Exit")
        choice = input("Please select an option (1-6): ")

        if choice == '1':
            task_description = input("Enter the task description: ")
            new_task = {"task": task_description, "done": False}
            tasks.append(new_task)
            save_tasks()
            print("Task added!")
            print("You selected Add a task.")
            input("\nPress Enter to continue...")
        elif choice == '2':
            display_tasks()
            print("You selected View all tasks.")
            input("\nPress Enter to continue...")
        elif choice == '3':
            if not tasks:
                print ("No tasks available to mark as complete.")
            else:
                display_tasks()
                try:
                    task_number = int(input("Enter the task number to mark as complete: "))
                    if 1 <= task_number <= len(tasks):
                        tasks[task_number - 1]["done"] = True
                        save_tasks()
                        print(f"Task {task_number} marked as complete.")
                    else:
                        print("Invalid task number.")
                except ValueError:
                    print("Please enter a valid number.")
            print("You selected Mark a task as complete.")
            input("\nPress Enter to continue...")
        elif choice == '4':
            if not tasks:
                print("No tasks available to remove.")
            else:
                display_tasks()
                try:
                    task_number = int(input("Enter the task number to remove: "))
                    if 1 <= task_number <= len(tasks):
                        removed_task = tasks.pop(task_number - 1)
                        save_tasks()
                        print(f"Removed task: {removed_task['task']}")
                    else:
                        print("Invalid task number.")
                except ValueError:
                    print("Please enter a valid number.")
            print("You selected Remove a task.")
            input("\nPress Enter to continue...")
        elif choice == '5':
            if not tasks:
                print("No tasks available to edit.")
            else:
                display_tasks()
                try:
                    task_number = int(input("Enter the task number to edit: "))
                    if 1 <= task_number <= len(tasks):
                        new_description = input("Enter the new task description: ")
                        tasks[task_number - 1]["task"] = new_description
                        save_tasks()
                        print(f"Task {task_number} updated to: {new_description}")
                    else:
                        print("Invalid task number.")
                except ValueError:
                    print("Please enter a valid number.")
            print("You selected Edit a task.")
            input("\nPress Enter to continue...")
        elif choice == '6':
            print("Exiting the menu. Goodbye!")
            save_tasks()
            break
        else:
            print("Invalid choice. Please try again.")
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    load_tasks()
    menu()