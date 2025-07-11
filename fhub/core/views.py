from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignUpForm, LoginForm
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

# ----------------------------- Authentication Views -----------------------------

@login_required
def home_views(request):
    #home page view after login
    return render(request, 'home.html')

def land_view(request):
    #landing page view (doesn't need login)
    return render(request, 'landing.html')

@csrf_protect
def signup_view(request):
    #Creating user account view
    form = SignUpForm()
    if request.method == 'POST':
        #if post request then authenticates and creates account
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # login(request, user) (naive) | redirecting again to login page is better
            return redirect('login') 
    #if the user is just viewing the signup page
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    #user login view
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                #Instead of using default username login using email to find user acc and login indirectly as email is easier to remember
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('home')
                else:
                    form.add_error(None, 'Invalid email or password.')
            except User.DoesNotExist:
                #error handling
                form.add_error('email', 'No account found with this email.')
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    #using default logout in djanog-authentication
    logout(request)
    return redirect('login')

# ----------------------------- Expense Views -----------------------------

from .models import Expense, Budget
from .forms import ExpenseForm, BudgetForm
from django.db.models import Sum
from datetime import date
from datetime import datetime, date
import calendar

@login_required
def expense_dashboard(request):
    #retrieving the user specific expenses
    expenses = Expense.objects.filter(user=request.user).order_by('-date')

    #getting the start and end date from filter bar form for filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    #for default filter bar (no user input in filter)
    current_year = date.today().year
    current_month = date.today().month

    # Filter expenses if start and end dates provided
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)

    if start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # Convert year & month into comparable values
        start_value = start.year * 12 + start.month
        end_value = end.year * 12 + end.month

        # Filter budgets correctly between start and end month/year
        budgets = Budget.objects.filter(user=request.user)
        total_budget = sum(
            b.amount for b in budgets
            if (b.year * 12 + b.month) >= start_value and (b.year * 12 + b.month) <= end_value
        )
    else:
        # Default to current month budget and expenses
        total_budget = Budget.objects.filter(
            user=request.user,
            year=current_year,
            month=current_month
        ).aggregate(total_budget=Sum('amount'))['total_budget'] or 0

        # Also filter expenses to current month if no filter is given
        expenses = Expense.objects.filter(
            user=request.user,
            date__year=current_year,
            date__month=current_month
        ).order_by('-date')

    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_budget - total_expenses

    #category summary for the pie chart visualisation
    category_summary = expenses.values('category').annotate(total=Sum('amount')).order_by('category')

    month_labels = [calendar.month_name[i] for i in range(1, 13)]
    month_totals = [
        Expense.objects.filter(user=request.user, date__year=current_year, date__month=month)
        .aggregate(Sum('amount'))['amount__sum'] or 0
        for month in range(1, 13)
    ]

    #handling the forms adding expense and updating budget
    if request.method == 'POST':
        if 'add_expense' in request.POST:
            expense_form = ExpenseForm(request.POST)
            budget_form = BudgetForm()
            if expense_form.is_valid():
                new_expense = expense_form.save(commit=False)
                new_expense.user = request.user
                new_expense.save()
                return redirect('expense-dashboard')
        elif 'set_budget' in request.POST:
            budget_form = BudgetForm(request.POST)
            expense_form = ExpenseForm()
            if budget_form.is_valid():
                Budget.objects.update_or_create(
                    user=request.user,
                    year=budget_form.cleaned_data['year'],
                    month=budget_form.cleaned_data['month'],
                    defaults={'amount': budget_form.cleaned_data['amount']}
                )
                return redirect('expense-dashboard')
    else:
        expense_form = ExpenseForm()
        budget_form = BudgetForm()

    #mapping the variables here to html
    context = {
        'expenses': expenses,
        'budget': total_budget,
        'total_expenses': total_expenses,
        'balance': balance,
        'expense_form': expense_form,
        'budget_form': budget_form,
        'category_summary': category_summary,
        'month_labels': month_labels,
        'month_totals': month_totals,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'expenses.html', context)


@login_required
def delete_expense(request, expense_id):
    #finding expense using requested expense id and delete
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    expense.delete()
    return redirect('expense-dashboard')

# ----------------------------- To DO list Views -----------------------------

from .models import Task
from .forms import TaskForm

@login_required
def todo_list(request):
    #filtering the tasks of user form database
    tasks = Task.objects.filter(user=request.user)
    todo = tasks.filter(status='todo')
    progress = tasks.filter(status='progress')
    completed = tasks.filter(status='completed')
    form = TaskForm()
    return render(request, 'todo.html', {
        'todo': todo,
        'progress': progress,
        'completed': completed,
        'form': form,
    })

@login_required
def add_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            #commit = false allows to change the object before saving it to database
            task = form.save(commit=False)
            task.user = request.user
            task.save()
    return redirect('todo_list')

@login_required
def delete_task(request, task_id):
    Task.objects.filter(id=task_id, user=request.user).delete()
    return redirect('todo_list')

@login_required
def toggle_task_status(request, task_id):
    task = Task.objects.get(id=task_id, user=request.user)
    task.status = 'completed' if task.status != 'completed' else 'todo'
    task.save()
    return redirect('todo_list')

# ----------------------------- Notes Views -----------------------------

from .models import Note
from .forms import NoteForm

@login_required
def notes_dashboard(request):
    #notes page view
    notes = Note.objects.filter(user=request.user, archived=False).order_by('-pinned', '-updated_at')

    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            #commit = false allows to change the object before saving it to database
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            return redirect('notes-dashboard')
    else:
        form = NoteForm()

    context = {
        'notes': notes,
        'form': form,
    }
    return render(request, 'notes.html', context)

@login_required
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    note.delete()
    return redirect('notes-dashboard')

@login_required
def toggle_pin(request, note_id):
    #pin the notes to important(displays first)
    note = get_object_or_404(Note, id=note_id, user=request.user)
    note.pinned = not note.pinned
    note.save()
    return redirect('notes-dashboard')
@login_required
def toggle_favorite(request, note_id):
    #toggling the note to favourite
    note = get_object_or_404(Note, id=note_id, user=request.user)
    note.is_favorite = not note.is_favorite
    note.save()
    return redirect('notes-dashboard')

def edit_note_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)

    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return redirect('notes')
    else:
        form = NoteForm(instance=note)

    return render(request, 'edit_note.html', {'form': form, 'note_to_edit': note})

def update_note_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return redirect('notes')
    else:
        form = NoteForm(instance=note)

    return render(request, 'edit_note.html', {'form': form, 'note_to_edit': note})

# ----------------------------- Calendar Views -----------------------------

from django.http import JsonResponse
from .models import CalendarEvent
import json
from django.views.decorators.csrf import csrf_exempt

@login_required
def calendar_page(request):
    return render(request, 'calendar.html') 

@login_required
def get_events(request):
    # brings all the user marked events
    events = CalendarEvent.objects.filter(user=request.user)
    events_data = [
        {
            'id': event.id,
            'title': event.title,
            'date': str(event.date),
            'time': str(event.time),
            'reminder': event.reminder,
            'color': event.color
        }
        for event in events
    ]
    return JsonResponse(events_data, safe=False)

@csrf_exempt
@login_required
def add_event(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        CalendarEvent.objects.create(
            user=request.user,
            title=data['title'],
            date=data['date'],
            time=data['time'],
            reminder=data.get('reminder'),
            color=data.get('color', '#6c63ff')
        )
        return JsonResponse({'message': 'Event added successfully!'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@login_required
def delete_event(request, event_id):
    if request.method == 'DELETE':
        CalendarEvent.objects.filter(id=event_id, user=request.user).delete()
        return JsonResponse({'message': 'Event deleted successfully!'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

# ----------------------------- Inventory Views -----------------------------

from .models import InventoryItem
from .forms import ItemForm

@login_required
def inventory_dashboard(request):
    #inventory page views
    items = InventoryItem.objects.filter(user=request.user)
    form = ItemForm()

    if request.method == 'POST' and 'item_id' not in request.POST:
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            return redirect('inventory-dashboard')

    context = {'items': items, 'form': form}
    return render(request, 'inventory.html', context)

@login_required
def edit_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id, user=request.user)
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect('inventory-dashboard')
    else:
        form = ItemForm(instance=item)
    return redirect('inventory-dashboard')

@login_required
def delete_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id, user=request.user)
    if request.method == 'POST' or request.method == 'GET':
        item.delete()
    return redirect('inventory-dashboard')
